import json
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from google.cloud import dialogflow

from dialogflow_fulfillment import WebhookClient

# Create your views here.
GOOGLE_PROJECT_ID = settings.GOOGLE_PROJECT_ID
msg_list = []
with open('chat_log.json', 'r') as f:
    msg_list = json.load(f)

@require_http_methods(['GET'])
def index(request):
    global msg_list
    with open('chat_log.json', 'r') as f:
        msg_list = json.load(f)
    return render(request, 'home.html', {'chat_log': msg_list})

@require_http_methods(['GET'])
def clear_log(request):
    global msg_list
    msg_list = []
    with open('chat_log.json', 'w') as f:
        json.dump([], f)
    return HttpResponse()

def convert(data):
    if isinstance(data, bytes):
        return data.decode('utf-8')
    if isinstance(data, dict):
        return dict(map(convert, data.items()))
    if isinstance(data, tuple):
        return map(convert, data)

    return data

@csrf_exempt
@require_http_methods(['POST'])
def chat(request):
    print('Body', request.body)
    input_dict = convert(request.body)
    input_text = json.loads(input_dict)['text'].strip()
    session_id = json.loads(input_dict)['room'].strip()

    # global msg_list
    # msg_list = request.session.get(session_id, [])
    # context_short_name = "does_not_matter"

    # context_name = "projects/" + GOOGLE_PROJECT_ID + "/agent/sessions/" + session_id + "/contexts/" + \
    #            context_short_name.lower()

    # parameters = dialogflow.types.struct_pb2.Struct()
    # #parameters["foo"] = "bar"

    # context_1 = dialogflow.types.context_pb2.Context(
    #     name=context_name,
    #     lifespan_count=2,
    #     parameters=parameters
    # )
    # query_params_1 = {"contexts": [context_1]}

    language_code = 'zh-TW'

    # response = detect_intent_with_parameters(
    #     project_id=GOOGLE_PROJECT_ID,
    #     session_id=session_id,
    #     query_params=query_params_1,
    #     language_code=language_code,
    #     user_input=input_text
    # )
    if input_text:
        msg_list.append("User: "+input_text)
        response = detect_intent_texts(
            GOOGLE_PROJECT_ID,
            session_id,
            input_text,
            language_code
        )
        for msg in response.query_result.fulfillment_messages:
            if not msg.platform:
                msg_list.append('Bot: '+msg.text.text[0])
        # request.session[session_id] = msg_list
        with open('chat_log.json', 'w') as f:
            json.dump(msg_list, f)

        return HttpResponse(response.query_result.fulfillment_text)
    return HttpResponse()

def detect_intent_texts(project_id, session_id, text, language_code):
    """Returns the result of detect intent with texts as inputs.

    Using the same `session_id` between requests allows continuation
    of the conversation."""
    session_client = dialogflow.SessionsClient()

    session = session_client.session_path(project_id, session_id)
    print('Session path: {}\n'.format(session))

    text_input = dialogflow.TextInput(
        text=text, language_code=language_code)

    query_input = dialogflow.QueryInput(text=text_input)

    response = session_client.detect_intent(
        request={'session': session, 'query_input': query_input})

    print('=' * 20)
    print('Query text: {}'.format(response.query_result.query_text))
    print('Detected intent: {} (confidence: {})\n'.format(
        response.query_result.intent.display_name,
        response.query_result.intent_detection_confidence))
    print('Fulfillment text: {}\n'.format(
        response.query_result.fulfillment_messages))

    return response

@csrf_exempt
@require_http_methods(['POST'])
def webhook(request):
    content = json.loads(convert(request.body))
    print(content)
    agent = WebhookClient(content)
    agent.handle_request(handler)
    response = agent.response

    return HttpResponse(json.dumps(response), content_type='application/json')

def handler(agent):
    # remove null message
    agent.console_messages = [msg for msg in agent.console_messages if msg.text.text.strip()]
    if agent.intent == 'detect.sentiment':
        score = sentiment_analysis(agent.query)
        agent.add('這句話的情緒分數是: {}'.format(score))

def sentiment_analysis(sentence):
    import jieba.posseg
    # Read sentiment dictionary
    with open('sentiment-dict/ntusd-positive.txt', encoding='utf-8') as f:
        positive = set(w.strip() for w in f.readlines())

    with open('sentiment-dict/ntusd-negative.txt', encoding='utf-8') as f:
        negative = set(w.strip() for w in f.readlines())

    # Calculate weighted term frequency
    term_frequency = {}
    for word, flag in jieba.posseg.cut(sentence):
        weight = 2 if flag.startswith('a') else 1
        term_frequency[word] = term_frequency[word] + weight if word in term_frequency else weight

    # Score sentiment
    positive_sentiment_score = 0
    negative_sentiment_score = 0
    for word, num in term_frequency.items():
        if word in positive:
            positive_sentiment_score += num
        if word in negative:
            negative_sentiment_score += num

    print("Pos:", positive_sentiment_score)
    print("Neg:", negative_sentiment_score)
    print("Sentiment:", (positive_sentiment_score-negative_sentiment_score))

    return positive_sentiment_score-negative_sentiment_score