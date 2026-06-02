import json
import os
from datetime import datetime

from flask import current_app, flash, jsonify, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from extensions import db
from models import CV
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


def _get_gemini_model():
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("Le package google-genai n'est pas installe.") from exc

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("La variable d'environnement GEMINI_API_KEY est absente.")

    return genai.Client(api_key=api_key)


class CVController:
    @staticmethod
    def index():
        cvs = CV.query.order_by(CV.uploaded_at.desc()).all()
        return render_template("index.html", cvs=cvs)

    @staticmethod
    def show(cv_id):
        cv = CV.query.get_or_404(cv_id)
        return render_template("cv_show.html", cv=cv)

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

            upload_dir = os.path.join(current_app.root_path, "uploads")
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
                "education": []
            }}
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

        db.session.delete(cv)
        db.session.commit()

        if _wants_json_response():
            return jsonify({"message": "CV supprime avec succes."})

        flash("CV supprimé avec succes.", "success")
        return redirect(url_for("cv.index"))
