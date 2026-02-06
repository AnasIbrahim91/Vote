from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Change in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///election.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class Voter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    has_voted = db.Column(db.Boolean, default=False)
    is_candidate = db.Column(db.Boolean, default=False)

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('voter.id'), nullable=False)
    votes = db.Column(db.Integer, default=0)

# Create tables
with app.app_context():
    db.create_all()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        voter_id = request.form.get('id')
        dob_str = request.form.get('dob')
        try:
            dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
            voter = Voter.query.filter_by(id=voter_id, dob=dob, has_voted=False).first()
            if voter:
                return redirect(url_for('vote', voter_id=voter_id))
            else:
                flash('Invalid ID, DOB, or you have already voted.')
        except ValueError:
            flash('Invalid date format.')
    return render_template('login.html')

@app.route('/vote/<int:voter_id>', methods=['GET', 'POST'])
def vote(voter_id):
    voter = Voter.query.get_or_404(voter_id)
    if voter.has_voted:
        flash('You have already voted.')
        return redirect(url_for('login'))
    
    candidates = Voter.query.filter_by(is_candidate=True).all()
    if request.method == 'POST':
        selected = request.form.getlist('candidates')
        if len(selected) != 9:
            flash('You must select exactly 9 candidates.')
            return render_template('vote.html', candidates=candidates, voter_id=voter_id)
        
        # Process votes atomically
        for cand_id in selected:
            vote_record = Vote.query.filter_by(candidate_id=int(cand_id)).first()
            if vote_record:
                vote_record.votes += 1
            else:
                new_vote = Vote(candidate_id=int(cand_id), votes=1)
                db.session.add(new_vote)
        voter.has_voted = True
        db.session.commit()
        flash('Vote submitted successfully!')
        return redirect(url_for('login'))
    
    return render_template('vote.html', candidates=candidates, voter_id=voter_id)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        # Handle file upload
        file = request.files.get('file')
        if file and file.filename.endswith('.xlsx'):
            df = pd.read_excel(file)
            for _, row in df.iterrows():
                dob = datetime.strptime(str(row['DOB']), '%Y-%m-%d').date()
                voter = Voter(id=row['ID'], name=row['Name'], dob=dob)
                db.session.add(voter)
            db.session.commit()
            flash('Voters uploaded successfully.')
        
        # Handle candidate setup
        candidate_ids = request.form.get('candidate_ids')
        if candidate_ids:
            ids = [int(x.strip()) for x in candidate_ids.split(',') if x.strip()]
            Voter.query.filter(Voter.id.in_(ids)).update({'is_candidate': True})
            db.session.commit()
            flash('Candidates set successfully.')
    
    # Live results
    results = db.session.query(Voter.name, Vote.votes).join(Vote, Voter.id == Vote.candidate_id).filter(Voter.is_candidate == True).all()
    return render_template('admin.html', results=results)

if __name__ == '__main__':
    app.run(debug=True)