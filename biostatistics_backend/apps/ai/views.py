from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .services import get_ai_tutor_response


class AIChatView(APIView):
    def get(self, request):
        return Response(
            {
                "messages": [
                    {"role": "user", "content": "p-value 0.06 деген не?"},
                    {
                        "role": "assistant",
                        "content": "Жақсы сұрақ. Сіздің ойыңызша p-value зерттеу нәтижесінің кездейсоқ шығу ықтималдығын көрсете ме?"
                    },
                    {"role": "user", "content": "Ол 0.05-тен үлкен, демек нәтиже маңызды емес қой, иә?"}
                ]
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        messages = request.data.get("messages")

        if not messages:
            single_message = request.data.get("message")

            if single_message:
                messages = [
                    {
                        "role": "user",
                        "content": single_message,
                    }
                ]
            else:
                return Response(
                    {"error": "messages is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            answer = get_ai_tutor_response(messages)

            return Response(
                {
                    "messages": messages,
                    "answer": answer,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {
                    "error": "AI request failed",
                    "details": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )