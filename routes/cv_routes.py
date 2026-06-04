from flask import Blueprint
from controllers.cv_controller import CVController

cv_bp = Blueprint("cv", __name__, url_prefix="/cvs")

cv_bp.add_url_rule("/", "index", CVController.index, methods=["GET"])
cv_bp.add_url_rule("/chatbot", "chatbot", CVController.chatbot, methods=["GET"])
cv_bp.add_url_rule("/chatbot/ask", "chatbot_ask", CVController.chatbot_ask, methods=["POST"])
cv_bp.add_url_rule("/chatbot/clear", "chatbot_clear", CVController.chatbot_clear, methods=["POST"])
cv_bp.add_url_rule("/upload", "upload", CVController.upload, methods=["POST"])
cv_bp.add_url_rule("/<int:cv_id>", "show", CVController.show, methods=["GET"])
cv_bp.add_url_rule("/<int:cv_id>/match-job", "match_job", CVController.match_job, methods=["POST"])
cv_bp.add_url_rule("/<int:cv_id>/delete", "delete", CVController.delete, methods=["POST"])
