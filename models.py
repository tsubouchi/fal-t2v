from app import db

class VideoGeneration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prompt = db.Column(db.Text, nullable=False)
    video_url = db.Column(db.String(512))
    status = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, server_default=db.func.now())
