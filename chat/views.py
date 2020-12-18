from django.conf import settings
from django.http import HttpResponse
from django.shortcut import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# Create your views here.
GOOGLE_PROJECT_ID = settings.GOOGLE_PROJECT_ID

@require_http_methods(['GET'])
def index(request):
    return render(request, 'home.html')

@csrf_exempt
@require_http_methods(['POST'])
def chat(request, session_id):
    print('Body', request.body)
    input_dict = convert(request.body)
    input_text = json.loads(input_dict)['text']

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
    response = detect_intent_texts(
        project_id,
        session_id,
        input_text,
        language_code
    )

    return HttpResponse(response.query_result.fulfillment_text, status=200)

def detect_intent_texts(project_id, session_id, texts, language_code):
    """Returns the result of detect intent with texts as inputs.

    Using the same `session_id` between requests allows continuation
    of the conversation."""
    from google.cloud import dialogflow
    session_client = dialogflow.SessionsClient()

    session = session_client.session_path(project_id, session_id)
    print('Session path: {}\n'.format(session))

    for text in texts:
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
            response.query_result.fulfillment_text))