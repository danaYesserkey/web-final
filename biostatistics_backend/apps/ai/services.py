from decouple import config
from openai import OpenAI

client = OpenAI(
    api_key=config("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

DATA_TYPES_MATERIAL = """
Деректер — фактілердің, сандардың, бақылаулардың немесе ақпараттардың жиынтығы.
Деректерді дұрыс түрге бөлу статистикалық әдісті дұрыс таңдауға көмектеседі.

Деректер екі негізгі топқа бөлінеді:
1) Сапалық деректер — нысанның қасиетін немесе категориясын сипаттайды. Оларға арифметикалық амал қолданылмайды.
   Түрлері: номиналды, реттік, бинарлы.
   Мысалдар: жыныс, диагноз, қан тобы, ауру сатысы, иә/жоқ.
2) Сандық деректер — нақты сандық мәнмен беріледі.
   Түрлері: дискретті және үздіксіз.
   Мысалдар: пациенттер саны, дәрігерге бару саны, температура, салмақ, бой, қан қысымы.

Қан тобы — сапалық номиналды дерек. Себебі ол A, B, AB, O сияқты категорияларды білдіреді; оларды өсу-кему ретімен орналастыруға немесе арифметикалық есептеуге болмайды.
"""

FORBIDDEN_KEYWORDS = [
    "код жаз", "python код", "пайтон код", "javascript", "java", "sql код",
    "эссе жаз", "реферат жаз", "дайын жауап бер", "тест жауабын бер",
    "куиз жауабын бер", "үй тапсырмасын шығарып бер",
]

REFUSAL_TEXT = (
    "Кешіріңіз, мен тек биостатистика ұғымдарын меңгеруге көмектесетін ассистентпін. "
    "Дайын код, эссе немесе тесттің тікелей жауабын бере алмаймын. "
    "Бірақ тақырыптың логикасын түсіндіріп, дұрыс ойлауға көмектесе аламын."
)


def is_forbidden_request(text: str) -> bool:
    text = (text or "").lower()
    return any(keyword in text for keyword in FORBIDDEN_KEYWORDS)


def trim_history(messages_history: list, limit: int = 8) -> list:
    """Keep request small so Groq does not cut or reject the answer."""
    if not isinstance(messages_history, list):
        return []
    return messages_history[-limit:]


def get_ai_tutor_response(messages_history: list) -> str:
    messages_history = trim_history(messages_history)

    last_user_message = ""
    for msg in reversed(messages_history):
        if msg.get("role") == "user":
            last_user_message = msg.get("content", "")
            break

    if is_forbidden_request(last_user_message):
        return REFUSAL_TEXT

    system_instruction = (
        "Сен биостатистика бойынша қазақ тілінде жауап беретін AI көмекшісің. "
        "Студент нақты сұрақ қойса, бірден дұрыс әрі түсінікті жауап бер.\n"
        "Жауап беру форматы:\n"
        "- Жауапты 2–3 қысқа сөйлеммен бер.\n"
        "- Алдымен нақты жауапты айт, кейін бір қысқа түсіндірме немесе мысал бер.\n"
        "- Ұзақ лекция, үлкен тізім және бірнеше абзац жазба.\n"
        "- Студент арнайы сұрамаса, 90 сөзден аспа.\n"
        "- Сұрақты қайта көшіріп жазба.\n"
        "- Бірінші сөйлемде нақты жауапты айт.\n"
        "- Кейін қысқа түсіндірме және қажет болса бір медициналық/биостатистикалық мысал бер.\n"
        "- Артық тізім, ұзақ лекция және қайталау жазба.\n"
        "- Жауапта ешқашан 'Сұрақ:' деген бөлім немесе тақырып жазба.\n"
        "- Студенттің сұрағын қайта көшіріп жазба.\n"
        "- Тест қатесін талқылағанда ғана дұрыс жауапты бірден айтпай, бағыттаушы сұрақ қой.\n"
        "Оқу материалы:\n"
        f"{DATA_TYPES_MATERIAL}"
    )

    full_messages = [{"role": "system", "content": system_instruction}]
    full_messages.extend(messages_history)

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=full_messages,
            temperature=0.1,
            max_tokens=500,
        )
        answer = response.choices[0].message.content
        if not answer or not answer.strip():
            return "Кешіріңіз, жауап қалыптаспады. Сұрағыңызды қайта жіберіңіз."
        return answer.strip()
    except Exception as e:
        return f"ИИ өңдеу қатесі: {str(e)}"
