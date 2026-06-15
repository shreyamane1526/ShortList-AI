def run_evaluation_async(application_id):
    """
    STEP 3: Async runner - spawns daemon thread for pipeline.
    """
    thread = threading.Thread(target=run_evaluation_pipeline, args=(application_id,))
    thread.daemon = True
    thread.start()


def run_evaluation_pipeline(application_id):
    """
    STEP 4: Main pipeline.
    1. Fetch app → candidate/job
    2. Create/reset CandidateJobEvaluation (for existing pipeline)
    3. Run existing run_pipeline → get result
    4. Update app.match_score, feedback_note (feedback), status etc. from result
    """
    from extensions import db
    from models import Application, CandidateJobEvaluation

    app = db.session.get(Application, application_id)
    if not app:
        return

    candidate = app.candidate
    job = app.job

    try:
        # Create or reset eval row for pipeline
        ev = CandidateJobEvaluation.query.filter_by(
            candidate_id=candidate.id,
            job_id=job.id
        ).first()
        if ev:
            ev.eval_status = "pending"
            ev.eval_error = None
        else:
            ev = CandidateJobEvaluation(
                candidate_id=candidate.id,
                job_id=job.id,
                eval_status="pending",
            )
            db.session.add(ev)
        db.session.commit()

        # 🔥 Run full evaluation pipeline (existing agents/Groq)
        result = run_pipeline(candidate.id, job.id)

        # Update application with results (STEP 2)
        app.match_score = int(result["score"])
        app.feedback_note = result["why_fit"]  # or generate_feedback_report snippet
        app.status = "completed"
        app.strengths = result.get("strengths", [])
        app.gaps = result.get("gaps", [])
        app.confidence = "High" if result["score"] >= 80 else "Medium" if result["score"] >= 60 else "Low"
        app.why_fit = result.get("why_fit")

        # Optional: trigger feedback report via existing async
        from agents import evaluate_candidate_for_job_async
        from app import app as flask_app
        evaluate_candidate_for_job_async(flask_app, ev.id)  # generates FeedbackReport if needed

    except Exception as e:
        app.status = "failed"
        app.feedback_note = f"Evaluation failed: {str(e)}"
        app.match_score = 0

    db.session.commit()

