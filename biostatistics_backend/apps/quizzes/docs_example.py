from drf_spectacular.utils import OpenApiExample

QUIZ_SUBMIT_REQUEST_SCHEMA = {
    'type': 'object',
    'required': ['answers'],
    'properties': {
        'answers': {
            'type': 'array',
            'items': {
                'oneOf': [
                    {
                        'type': 'object',
                        'title': 'MCQAnswer',
                        'required': ['question_type', 'question_id', 'selected_choice'],
                        'properties': {
                            'question_type': {'type': 'string', 'enum': ['mcq']},
                            'question_id': {'type': 'integer'},
                            'selected_choice': {'type': 'integer'},
                        },
                    },
                    {
                        'type': 'object',
                        'title': 'TextAnswer',
                        'required': ['question_type', 'question_id', 'text_response'],
                        'properties': {
                            'question_type': {'type': 'string', 'enum': ['text']},
                            'question_id': {'type': 'integer'},
                            'text_response': {'type': 'string'},
                        },
                    },
                ]
            },
        }
    },
}

QUIZ_SUBMIT_RESPONSE_SCHEMA = {
    'type': 'object',
    'properties': {
        'id': {'type': 'integer'},
        'quiz': {'type': 'integer'},
        'total_questions': {'type': 'integer'},
        'score': {'type': 'integer'},
        'score_percentage': {'type': 'number', 'format': 'float'},
        'completed_at': {'type': 'string', 'format': 'date-time'},
        'passed': {'type': 'boolean'},
        'results': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'question_id': {'type': 'integer'},
                    'question_type': {'type': 'string', 'enum': ['mcq', 'text']},
                    'text': {'type': 'string'},
                    'is_correct': {'type': 'boolean'},
                    'user_answer': {
                        'oneOf': [{'type': 'integer'}, {'type': 'string'}],
                        'nullable': True,
                    },
                    'correct_answer': {
                        'oneOf': [{'type': 'integer'}, {'type': 'string'}],
                        'nullable': True,
                    },
                },
            },
        },
    },
}

LESSON_RESPONSE_SCHEMA = {
    'type': 'object',
    'properties': {
        'id': {'type': 'integer'},
        'module': {'type': 'integer'},
        'lesson_name': {'type': 'string'},
        'order': {'type': 'integer'},
        'contents': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'order': {'type': 'integer'},
                    'content': {'type': 'string'},
                    'type': {'type': 'string', 'enum': ['text', 'image', 'video', 'presentation']},
                },
            },
        },
    },
}


QUIZ_SUBMIT_EXAMPLE = OpenApiExample(
    name='Submit quiz example',
    request_only=True,
    value={
        "answers": [
            {
                "question_id": 4,
                "question_type": "mcq",
                "user_answer": 10
            },
            {
                "question_id": 5,
                "question_type": "birneshe",
                "user_answer": [14, 15]
            },
            {
                "question_id": 6,
                "question_type": "text",
                "user_answer": "T-test"
            },
            {
                "question_id": 7,
                "question_type": "mcq",
                "user_answer": 16
            }
        ]
    }
)

QUIZ_RESULT_EXAMPLE = OpenApiExample(
    name='Quiz result after submit',
    response_only=True,
    status_codes=['200'],
    value={
        "quiz": 1,
        "total_questions": 4,
        "score": 3,
        "score_percentage": 75.0,
        "completed_at": "2026-06-18T12:03:37.730615Z",
        "passed": False,
        "results": [
            {
                "question_id": 4,
                "question_type": "mcq",
                "text": "Based on given dataset file, which t-test value is correct?",
                "is_correct": True,
                "user_answer": 10,
                "correct_answer": 10
            },
            {
                "question_id": 5,
                "question_type": "birneshe",
                "text": "In which scenarios from the case can be t-test applied?",
                "is_correct": True,
                "user_answer": [14, 15],
                "correct_answer": [14, 15]
            },
            {
                "question_id": 6,
                "question_type": "text",
                "text": "Which method is best for our case?",
                "is_correct": True,
                "user_answer": "T-test",
                "correct_answer": "T-test"
            },
            {
                "question_id": 7,
                "question_type": "mcq",
                "text": "What is best way to describe data?",
                "is_correct": False,
                "user_answer": 16,
                "correct_answer": 17
            }
        ]
    }
)

FIRST_ATTEMPT_EXAMPLE = OpenApiExample(
    name='First quiz submit',
    summary='User submits quiz for the first time',
    response_only=True,
    status_codes=['200'],
    value={
        "id": 1,
        "blocks": [
            {
                "context": {
                    "title": "Case analysis for t-test",
                    "text": "Here given dataset file and inside file...",
                    "dataset_file": "/media/derek/case_t_test.csv"
                },
                "questions": [
                    {
                        "id": 4,
                        "text": "Based on given dataset file, which t-test value is correct?",
                        "answer_options": [
                            {
                                "id": 9,
                                "text": "0.2"
                            },
                            {
                                "id": 10,
                                "text": "0.5"
                            },
                            {
                                "id": 11,
                                "text": "0.95"
                            },
                            {
                                "id": 12,
                                "text": "0.76"
                            }
                        ],
                        "question_type": "mcq"
                    },
                    {
                        "id": 5,
                        "text": "In which scenarios from the case can be t-test applied?",
                        "answer_options": [
                            {
                                "id": 13,
                                "text": "All of them"
                            },
                            {
                                "id": 14,
                                "text": "For 3-scenario"
                            },
                            {
                                "id": 15,
                                "text": "For 4-scenario"
                            },
                            {
                                "id": 20,
                                "text": "None of them"
                            }
                        ],
                        "question_type": "birneshe"
                    },
                    {
                        "id": 6,
                        "text": "Which method is best for our case?",
                        "question_type": "text"
                    }
                ]
            },
            {
                "context": None,
                "questions": [
                    {
                        "id": 7,
                        "text": "What is best way to describe data?",
                        "answer_options": [
                            {
                                "id": 16,
                                "text": "Using modeling"
                            },
                            {
                                "id": 17,
                                "text": "Using statistics"
                            },
                            {
                                "id": 18,
                                "text": "Telling data"
                            },
                            {
                                "id": 19,
                                "text": "Applying formula"
                            }
                        ],
                        "question_type": "mcq"
                    }
                ]
            }
        ],
        "passed": False,
        "total_questions": 4,
        "score": None,
        "score_percentage": None,
        "title": "1-quiz",
        "lesson": 1
    }
)

LAST_ATTEMPT_EXAMPLE = OpenApiExample(
    name='Previous attempt exists',
    summary='Previous quiz results',
    response_only=True,
    status_codes=['200'],
    value={
        "id": 1,
        "blocks": [
            {
                "context": {
                    "title": "Case analysis for t-test",
                    "text": "Here given dataset file and inside file...",
                    "dataset_file": "/media/derek/case_t_test.csv"
                },
                "questions": [
                    {
                        "id": 4,
                        "text": "Based on given dataset file, which t-test value is correct?",
                        "answer_options": [
                            {
                                "id": 9,
                                "text": "0.2"
                            },
                            {
                                "id": 10,
                                "text": "0.5"
                            },
                            {
                                "id": 11,
                                "text": "0.95"
                            },
                            {
                                "id": 12,
                                "text": "0.76"
                            }
                        ],
                        "question_type": "mcq",
                        "user_answer": 10,
                        "is_correct": True,
                        "correct_answer": 10
                    },
                    {
                        "id": 5,
                        "text": "In which scenarios from the case can be t-test applied?",
                        "answer_options": [
                            {
                                "id": 13,
                                "text": "All of them"
                            },
                            {
                                "id": 14,
                                "text": "For 3-scenario"
                            },
                            {
                                "id": 15,
                                "text": "For 4-scenario"
                            },
                            {
                                "id": 20,
                                "text": "None of them"
                            }
                        ],
                        "question_type": "birneshe",
                        "user_answer": [
                            14,
                            15
                        ],
                        "is_correct": True,
                        "correct_answer": [
                            14,
                            15
                        ]
                    },
                    {
                        "id": 6,
                        "text": "Which method is best for our case?",
                        "question_type": "text",
                        "user_answer": "T-test",
                        "is_correct": True,
                        "correct_answer": "T-test"
                    }
                ]
            },
            {
                "context": None,
                "questions": [
                    {
                        "id": 7,
                        "text": "What is best way to describe data?",
                        "answer_options": [
                            {
                                "id": 16,
                                "text": "Using modeling"
                            },
                            {
                                "id": 17,
                                "text": "Using statistics"
                            },
                            {
                                "id": 18,
                                "text": "Telling data"
                            },
                            {
                                "id": 19,
                                "text": "Applying formula"
                            }
                        ],
                        "question_type": "mcq",
                        "user_answer": 16,
                        "is_correct": False,
                        "correct_answer": 17
                    }
                ]
            }
        ],
        "passed": False,
        "total_questions": 4,
        "score": 3,
        "score_percentage": 75.0,
        "title": "1-quiz",
        "lesson": 1
    }
)