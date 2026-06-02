from flask import Blueprint
from controllers.analysis_controller import AnalysisController

analysis_bp = Blueprint("analysis", __name__, url_prefix="/analysis")

analysis_bp.add_url_rule(
    "/<int:cv_id>/generate",
    "generate",
    AnalysisController.generate,
    methods=["POST"],
)

analysis_bp.add_url_rule(
    "/<int:cv_id>",
    "result",
    AnalysisController.result,
    methods=["GET"],
)