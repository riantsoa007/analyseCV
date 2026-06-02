from datetime import datetime

from extensions import db


class Analysis(db.Model):
    __tablename__ = "analyses"

    id = db.Column(db.Integer, primary_key=True)
    analysis_text = db.Column(db.Text)
    suggestions = db.Column(db.Text)
    score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    cv_id = db.Column(db.Integer, db.ForeignKey("cvs.id"), nullable=False)
