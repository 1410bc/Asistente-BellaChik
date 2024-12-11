from flask import Flask, request, jsonify
import requests
import functions
import openai
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

creds = functions.authenticate_google()

@app.route('/', methods=['GET'])
def home():
    return 'Servidor Activo'

@app.route('/chat_assistant', methods=['POST'])
def chat_assistant():
    try:
        from pprint import pprint

        data = request.get_json()

        if data is None or 'message' not in data:
            return jsonify({'status': 'error', 'message': 'Se requiere un campo "message" en el JSON.'}), 400

        user_message = data['message']
        assistant_id = os.getenv("ASSISTANT_ID")

        # Crear un hilo de conversación
        thread = openai.beta.threads.create()
        print(thread.id)

        # Agregar el mensaje del usuario al hilo
        openai.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_message,
        )

        # Ejecutar el asistente
        run = openai.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant_id,
        )
        print("1" + run.id)

        run = openai.beta.threads.runs.retrieve(
        thread_id=thread.id,
        run_id=run.id,
        )
        print(run.status)

        # Verificar el estado de la ejecución
        while run.status not in ("completed", "failed", "requires_action"):
            run = openai.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id,
            )

        print("2" + run.status)

        if run.status == "requires_action":
            print("Hola")
            tools_to_call = run.required_action.submit_tool_outputs.tool_calls
            print(tools_to_call[0].function.name)
            print(tools_to_call[0].function.arguments)

            if(tools_to_call[0].function.name == "create_google_calendar_event"):
                datos = tools_to_call[0].function.arguments
                
                datos_dict = json.loads(datos)  # Asume que 'datos' es un string en formato JSON
        
                # Extraer los valores necesarios
                event_title = datos_dict.get("event_title", "Evento sin título")
                start_time = datos_dict.get("start_time", None)

                if start_time:
                    start_time_dt = datetime.fromisoformat(start_time)  # Asegúrate de que start_time esté en formato ISO 8601
                    end_time_dt = start_time_dt + timedelta(hours=1)
                    end_time = end_time_dt.isoformat()  # Convertir de nuevo a string en formato ISO 8601
                else:
                    end_time = None
                
                print(end_time)
                print(event_title)
                print(start_time)

                # Llamar a la función con los parámetros descompuestos
                functions.create_google_calendar_event(creds, event_title, start_time, end_time)

            elif(tools_to_call[0].function.name == "delete_google_calendar_event"):
                print("CANCELAR")
                datos = tools_to_call[0].function.arguments
                datos_dict = json.loads(datos)
                event_title = datos_dict.get("event_title", "Evento sin título")
                start_time = datos_dict.get("start_time", None)

                print(event_title)
                print(start_time)

                functions.delete_google_calendar_event_by_details(creds, event_title, start_time)

            #CONSULTAR EVENTOS
            elif(tools_to_call[0].function.name == "get_google_calendar_events"):
                time_min = datetime.now(timezone.utc).isoformat()
                time_min_datetime = datetime.now(timezone.utc)
                time_max_datetime = time_min_datetime + timedelta(weeks=1)
                time_max = time_max_datetime.isoformat()
                print(time_min)
                print(time_max)

                functions.get_google_calendar_events(creds, time_min, time_max)
            
            elif(tools_to_call[0].function.name == "update_google_calendar_event_by_details"):
                print("Funcion modificar")
                datos = tools_to_call[0].function.arguments
                datos_dict = json.loads(datos)# Asume que 'datos' es un string en formato JSON

                event_title = datos_dict.get("event_title", "Evento sin título")
                start_time = datos_dict.get("start_time", None)
                updated_title = datos_dict.get("updated_title", None)
                updated_start = datos_dict.get("updated_start", None)
                if updated_start:
                    updated_start_dt = datetime.fromisoformat(updated_start)  # Esto asume que 'updated_start' está en formato ISO 8601
                    updated_end_dt = updated_start_dt + timedelta(hours=1)
                    updated_end = updated_end_dt.isoformat()
                else:
                    updated_end = None

                print(event_title)
                print(updated_start)
                print(updated_end)
                
                functions.update_google_calendar_event_by_details(creds, event_title, start_time, updated_title=updated_title,updated_start=updated_start,updated_end=updated_end)

            tools_output_array = [({"tool_call_id": tools_to_call[0].id, "output": str(True)})]
            print(tools_output_array)
        
            run = openai.beta.threads.runs.submit_tool_outputs(
                thread_id=thread.id,
                run_id=run.id,
                tool_outputs=tools_output_array
                )
            print("3" + run.status)
        
        run = openai.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        print("4" + run.status)

        while run.status not in ("completed", "failed", "requires_action"):
            run = openai.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id,
            )

        print("5" + run.status)

        # Obtener los mensajes de la conversación
        messages = openai.beta.threads.messages.list(
            thread_id=thread.id,
        )

        # Construir la respuesta
        responses = []
        for each in messages:
            role = each.role
            content = each.content[0].text.value
            responses.append({'role': role, 'content': content})
            pprint(f"{role}: {content}")  # Imprimir en consola para depuración

        # Retornar los mensajes como respuesta
        return jsonify({'status': 'success', 'messages': responses}), 200

    except Exception as e:
        # Manejar errores inesperados
        return jsonify({'status': 'error', 'message': f'Error inesperado: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)