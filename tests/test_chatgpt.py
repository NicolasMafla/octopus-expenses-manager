from config.config import OPEN_AI_API_KEY
from src.service.chatgpt_analyzer import ChatGptAnalyzer
from openai import OpenAI


def test_gmail_service():
    chat = ChatGptAnalyzer(model="gpt-4o-mini", api_key=OPEN_AI_API_KEY)
    assert isinstance(chat._client, OpenAI)

    email = {
        'id': '195f988dd90cbffa',
        'mimeType': 'text/html',
        'sender': '"Banco enlínea" <bancaenlinea@Banco.com>',
        'recipient': 'john.doe@gmail.com',
        'date': '2 Apr 2025 21:44:09 -0500',
        'subject': 'Transferencia enviada por $223.00 desde Banco',
        'text': 'Banco enlínea notificacion nuevo formato Estimado/a John Doe Fecha y Hora: 2/Abril/2025 21:43 Transacción: Transferencia Enviada Exitosamente desde Banco Detalle Contacto: John DoeBanco Contacto: BANCO SUPERCuenta Contacto: XXXXX82326Monto: $223.00Descripción: Pago RociCanal: App MóvilReferencia: 0898982222 Esta transacción tiene un costo de $0.21 por motivo de Transferencia Interbancaria. Si no realizaste esta transacción por favor comunícate de manera urgente con nosotros a nuestro Call Center. Por favor no respondas a este mail. Atentamente Banco Si tienes alguna consulta con respecto a esta información no dudes en comunicarte con nosotros, caso contrario no es necesario responder a este correo electrónico.La información y adjuntos contenidos en este mensaje son confidenciales y reservados; por tanto no pueden ser usados, reproducidos o divulgados por otras personas distintas a su(s) destinatario(s). Si no eres el destinatario de este email, te solicitamos comedidamente eliminarlo. Cualquier opinión expresada en este mensaje, corresponde a su autor y no necesariamente al Banco.Recuerda que Banco nunca te requerirá por ningún medio, tu usuario o clave de acceso a sus sitios web o aplicaciones móviles.Te recomendamos no imprimir este correo electrónico a menos que sea estrictamente necesario.'
    }

    system_prompt = f"""
    You are a expert in analyzing information from the body of emails identifying which emails corresponds to
    credit cards consumptions and bank transfers of money. 
    """
    user_prompt = f"""
    The information of the email has been processed in the following dict object {email}, and are in spanish language. 
    
    I want you to use the information in the keys ('subject', 'text') to extract in case of cards consumptions or 
    bank transfers: 
    - If is a card consumption or bank transfer
    - Transaction type ('card' or 'transfer')
    - Amount
    - Establishment (In case of credit card consumption)
    - Beneficiary (In case of bank transfers)
    - Date

    Return the information in JSON format with the following keys:
    - "is_transaction" (bool)
    - "transaction_type" (str)
    - "amount" (float)
    - "establishment" (string)
    - "beneficiary" (string)
    - "date" (date, in YYYY-MM-DD format)
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    answer = chat.invoke(messages=messages)
    assert answer == {
        "is_transaction": True,
        "transaction_type": "transfer",
        "amount": 223.0,
        "establishment": "",
        "beneficiary": "BANCO SUPER",
        "date": "2025-04-02"
    }
