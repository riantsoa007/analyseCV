from datetime import datetime

from extensions import db


class CV(db.Model):
    __tablename__ = "cvs"

    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    extracted_text = db.Column(db.JSON, nullable=True)

    analysis = db.relationship("Analysis", backref="cv", uselist=False)
