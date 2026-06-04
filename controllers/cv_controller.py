import json
import os
from datetime import datetime

from flask import current_app, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from extensions import db
from models import Analysis, CV
from services.chroma_cv_store import ChromaCVStore
from services.cv_chatbot_service import CVChatbotService
from services.pdf_parser import PDFParser


def _wants_json_response():
    return request.accept_mimetypes["application/json"] > request.accept_mimetypes["text/html"]


def _extract_json_payload(raw_text):
    cleaned_text = (raw_text or "").strip()

    if cleaned_text.startswith("```"):
        parts = cleaned_text.split("```")
        if len(parts) >= 3:
            cleaned_text = parts[1]
            if cleaned_text.lower().startswith("json"):
                cleaned_text = cleaned_text[4:]
            cleaned_text = cleaned_text.strip()

    return json.loads(cleaned_text)


def _normalize_suggestions(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _normalize_score(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _decode_suggestions(value):
    if not value:
        return []

    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError, ValueError):
        return [str(value)]

    return _normalize_suggestions(parsed)


def _normalize_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _get_gemini_model():
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("Le package google-genai n'est pas installe.") from exc

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("La variable d'environnement GEMINI_API_KEY est absente.")

    return genai.Client(api_key=api_key)


def _build_show_context(cv, job_offer_text="", job_match_result=None):
    suggestions = _decode_suggestions(cv.analysis.suggestions) if cv.analysis else []
    return {
        "cv": cv,
        "suggestions": suggestions,
        "job_offer_text": job_offer_text,
        "job_match_result": job_match_result,
    }


def _get_chat_history():
    return session.get("cv_chat_history", [])


def _save_chat_history(history):
    session["cv_chat_history"] = history[-10:]


def _build_chatbot_context(question_text=""):
    history = _get_chat_history()
    cvs = CV.query.order_by(CV.uploaded_at.desc()).all()

    return {
        "chat_history": history,
        "question_text": question_text,
        "cv_count": len(cvs),
        "recent_cvs": cvs[:5],
    }


def _analyze_job_offer(cv, job_offer_text):
    client = _get_gemini_model()

    cv_payload = {
        "cv_id": cv.id,
        "file_name": cv.file_name,
        "extracted_text": cv.extracted_text or {},
        "analysis": {
            "analysis_text": cv.analysis.analysis_text if cv.analysis else None,
            "suggestions": _decode_suggestions(cv.analysis.suggestions) if cv.analysis else [],
            "score": cv.analysis.score if cv.analysis else None,
        },
    }

    prompt = f"""
    Analyse en francais la compatibilite entre cette offre de job et ce CV.
    Retourne UNIQUEMENT un JSON valide.

    Offre de job:
    {job_offer_text}

    Donnees du CV:
    {json.dumps(cv_payload, ensure_ascii=True, indent=2)}

    Format attendu:
    {{
        "match": true,
        "score": 0,
        "summary": "",
        "strengths": [],
        "missing_skills": [],
        "recommendation": ""
    }}

    Regles:
    - "match" doit etre true si le CV correspond globalement a l'offre, sinon false.
    - "score" doit etre un nombre entre 0 et 100.
    - "summary" doit etre un court resume en francais.
    - "strengths" doit lister les points forts du candidat par rapport a l'offre.
    - "missing_skills" doit lister les competences ou experiences manquantes.
    - "recommendation" doit donner une conclusion breve en francais.
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    try:
        result = _extract_json_payload(response.text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return {
            "raw": response.text,
            "match": False,
            "score": None,
            "summary": "Le resultat n'a pas pu etre converti en JSON.",
            "strengths": [],
            "missing_skills": [],
            "recommendation": "",
        }

    return {
        "match": bool(result.get("match")),
        "score": _normalize_score(result.get("score")),
        "summary": str(result.get("summary", "")).strip(),
        "strengths": _normalize_list(result.get("strengths")),
        "missing_skills": _normalize_list(result.get("missing_skills")),
        "recommendation": str(result.get("recommendation", "")).strip(),
    }


class CVController:
    @staticmethod
    def index():
        cvs = CV.query.order_by(CV.uploaded_at.desc()).all()
        return render_template("index.html", cvs=cvs)

    @staticmethod
    def chatbot():
        return render_template("chatbot.html", **_build_chatbot_context())

    @staticmethod
    def chatbot_ask():
        question = (request.form.get("question") or "").strip()

        if not question:
            message = "Veuillez saisir une question."
            if _wants_json_response():
                return jsonify({"error": message}), 400
            flash(message, "danger")
            return render_template("chatbot.html", **_build_chatbot_context(question_text=question))

        history = _get_chat_history()

        try:
            result = CVChatbotService.answer(
                question=question,
                history=history,
                ollama_model=current_app.config["OLLAMA_MODEL"],
                chroma_path=current_app.config["CHROMA_CV_PATH"],
                chroma_collection=current_app.config["CHROMA_CV_COLLECTION"],
                ollama_host=current_app.config["OLLAMA_HOST"],
            )
        except Exception as exc:
            message = f"Erreur pendant la reponse du chatbot : {exc}"
            if _wants_json_response():
                return jsonify({"error": message}), 500
            flash(message, "danger")
            return render_template("chatbot.html", **_build_chatbot_context(question_text=question))

        history.extend(
            [
                {"role": "user", "content": question},
                {"role": "assistant", "content": result["answer"]},
            ]
        )
        _save_chat_history(history)

        if _wants_json_response():
            return jsonify(
                {
                    "question": question,
                    "answer": result["answer"],
                    "candidate_cv_ids": [cv.id for cv in result["candidate_cvs"]],
                }
            )

        return render_template("chatbot.html", **_build_chatbot_context())

    @staticmethod
    def chatbot_clear():
        session.pop("cv_chat_history", None)

        if _wants_json_response():
            return jsonify({"message": "Historique efface."})

        flash("Historique du chatbot efface.", "success")
        return redirect(url_for("cv.chatbot"))

    @staticmethod
    def show(cv_id):
        cv = CV.query.get_or_404(cv_id)
        return render_template("cv_show.html", **_build_show_context(cv))

    @staticmethod
    def match_job(cv_id):
        cv = CV.query.get_or_404(cv_id)
        job_offer_text = (request.form.get("job_offer") or "").strip()

        if not job_offer_text:
            message = "Veuillez saisir une offre de job."
            if _wants_json_response():
                return jsonify({"error": message}), 400
            flash(message, "danger")
            return render_template(
                "cv_show.html",
                **_build_show_context(cv, job_offer_text=job_offer_text),
            )

        try:
            job_match_result = _analyze_job_offer(cv, job_offer_text)
        except Exception as exc:
            message = f"Erreur pendant l'analyse de l'offre : {exc}"
            if _wants_json_response():
                return jsonify({"error": message}), 500
            flash(message, "danger")
            return render_template(
                "cv_show.html",
                **_build_show_context(cv, job_offer_text=job_offer_text),
            )

        if _wants_json_response():
            return jsonify(
                {
                    "message": "Analyse de correspondance terminee.",
                    "cv_id": cv.id,
                    "job_offer": job_offer_text,
                    "result": job_match_result,
                }
            )

        return render_template(
            "cv_show.html",
            **_build_show_context(
                cv,
                job_offer_text=job_offer_text,
                job_match_result=job_match_result,
            ),
        )

    @staticmethod
    def upload():
        file = request.files.get("file")

        try:
            if not file or not file.filename:
                message = "Veuillez selectionner un fichier PDF."
                if _wants_json_response():
                    return jsonify({"error": message}), 400
                flash(message, "danger")
                return redirect(url_for("cv.index"))

            upload_dir = current_app.config["UPLOAD_FOLDER"]
            os.makedirs(upload_dir, exist_ok=True)

            safe_name = secure_filename(file.filename)
            stored_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{safe_name}"
            absolute_file_path = os.path.join(upload_dir, stored_name)
            relative_file_path = os.path.join("uploads", stored_name)
            file.save(absolute_file_path)

            text = PDFParser.extract_text(absolute_file_path)

            client = _get_gemini_model()
            prompt = f"""
            Extract structured information from this CV and return ONLY JSON:

            {text}

            Format:
            {{
                "name": "",
                "email": "",
                "skills": [],
                "experience": [],
                "education": [],
                "analysis": "",
                "suggestions": [],
                "score": 0
            }}

            Rules:
            - "analysis" must be a short professional summary of the profile et en francais.
            - "suggestions" must contain concrete recommendations to improve the CV or profile et en francais.
            - "score" must be a numeric score between 0 and 100 et en francais.
            """

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )

            try:
                extracted_json = _extract_json_payload(response.text)
            except (json.JSONDecodeError, TypeError, ValueError):
                extracted_json = {"raw": response.text}

            cv = CV(
                file_name=file.filename,
                file_path=relative_file_path,
                extracted_text=extracted_json,
            )

            db.session.add(cv)
            db.session.flush()

            analysis = Analysis(
                analysis_text=str(extracted_json.get("analysis", "")).strip() or None,
                suggestions=json.dumps(
                    _normalize_suggestions(extracted_json.get("suggestions")),
                    ensure_ascii=True,
                ),
                score=_normalize_score(extracted_json.get("score")),
                cv_id=cv.id,
            )

            db.session.add(analysis)
            ChromaCVStore.upsert_cv(
                current_app.config["CHROMA_CV_PATH"],
                cv,
                text,
                current_app.config["CHROMA_CV_COLLECTION"],
            )
            db.session.commit()

            if _wants_json_response():
                return jsonify(
                    {
                        "message": "CV uploaded and analyzed",
                        "cv_id": cv.id,
                        "data": extracted_json,
                    }
                )

            flash("CV uploadé et analysé avec succes.", "success")
            return redirect(url_for("cv.index"))
        except Exception as exc:
            db.session.rollback()

            message = f"Erreur pendant l'analyse du CV : {exc}"
            if _wants_json_response():
                return jsonify({"error": message}), 500

            flash(message, "danger")
            return redirect(url_for("cv.index"))

    @staticmethod
    def delete(cv_id):
        cv = CV.query.get_or_404(cv_id)
        absolute_file_path = os.path.join(current_app.root_path, cv.file_path)

        if os.path.exists(absolute_file_path):
            os.remove(absolute_file_path)

        try:
            ChromaCVStore.delete_cv(
                current_app.config["CHROMA_CV_PATH"],
                cv.id,
                current_app.config["CHROMA_CV_COLLECTION"],
            )
        except RuntimeError:
            pass

        db.session.delete(cv)
        db.session.commit()

        if _wants_json_response():
            return jsonify({"message": "CV supprime avec succes."})

        flash("CV supprimé avec succes.", "success")
        return redirect(url_for("cv.index"))
