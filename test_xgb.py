from agents.ranking_agent.predictor import (
    predict_score
)

test = {
    "reasoning_score": 85,
    "fit_score": 80,
    "trust_score": 78,
    "critical_gaps": 1,
    "moderate_gaps": 1,
    "nd_strengths": 2,
    "recommendation_score": 2,
}

result = predict_score(test)

print(result)