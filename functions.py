from flask import Flask, request, jsonify
import requests
import os
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, timezone
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from pprint import pprint
import pickle
import sys

SCOPES = ['https://www.googleapis.com/auth/calendar']

#Autenticacion de google
def authenticate_google():
    """
    Maneja la autenticación con Google y devuelve las credenciales.
    """
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES
            )
            creds = flow.run_local_server(port=8080)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds

def create_google_calendar_event(creds, event_title, start_time, end_time):

    # Construir el servicio de Google Calendar
    service = build('calendar', 'v3', credentials=creds)

    # Definir el evento
    event = {
        'summary': event_title,
        'start': {
            'dateTime': start_time,
            'timeZone': 'America/Mexico_City',
        },
        'end': {
            'dateTime': end_time,
            'timeZone': 'America/Mexico_City',
        },
    }

    # Crear el evento
    event_result = service.events().insert(
        calendarId='c_5429309c7c93803f3c31f144ef187db179ada2d6ad3d527aba230d3293704913@group.calendar.google.com', 
        body=event
    ).execute()
    
    print(f"Evento creado: {event_result.get('htmlLink')}")
    return event_result

def get_google_calendar_events(creds, time_min, time_max):

    service = build('calendar', 'v3', credentials=creds)

    events_result = service.events().list(
        calendarId='c_5429309c7c93803f3c31f144ef187db179ada2d6ad3d527aba230d3293704913@group.calendar.google.com',  # Cambia por tu ID de calendario si no usas el principal
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(f"Evento: {event['summary']}, Inicio: {start}")
    return events

def update_google_calendar_event_by_details(creds, event_title, start_time, updated_title=None, updated_start=None, updated_end=None):
    service = build('calendar', 'v3', credentials=creds)

    try:
        # Ajustar el rango de búsqueda (±1 minuto para tolerancia)
        
        start_datetime = datetime.fromisoformat(start_time)
        time_min = (start_datetime - timedelta(minutes=1)).isoformat() + "Z"
        time_max = (start_datetime + timedelta(minutes=1)).isoformat() + "Z"
        start_time_z = (start_datetime).isoformat() +"Z"

        print("Ya entró")
        print(start_time_z)

        events = get_google_calendar_events(creds,time_min, time_max)
        print(events)

        # Buscar el evento que coincide con el título y la hora de inicio
        for event in events:
            if event['summary'] == event_title and event['start']['dateTime'] == start_time_z:
                # Actualizar campos si se proporcionan
                if updated_title:
                    event['summary'] = updated_title
                if updated_start:
                    event['start']['dateTime'] = updated_start
                if updated_end:
                    event['end']['dateTime'] = updated_end

                print(event)
                sys.exit()

                # Actualizar el evento en Google Calendar
                updated_event = service.events().update(
                    calendarId='c_5429309c7c93803f3c31f144ef187db179ada2d6ad3d527aba230d3293704913@group.calendar.google.com',
                    eventId=event['id'],
                    body=event
                ).execute()
                
                
                print(f"Evento actualizado: {updated_event.get('htmlLink')}")
                return updated_event

        # Si no se encuentra ningún evento
        print(f"No se encontró un evento con el título '{event_title}' y la hora de inicio '{start_time}'.")
        return {"status": "not_found", "message": f"No se encontró un evento con el título '{event_title}' y la hora de inicio '{start_time}'."}

    except Exception as e:
        print(f"Error al actualizar el evento: {str(e)}")
        return {"status": "error", "message": str(e)}


def delete_google_calendar_event_by_details(creds, event_title, start_time):
    service = build('calendar', 'v3', credentials=creds)

    try:
        # Ajustar el rango de búsqueda (±1 minuto para tolerancia)
        start_datetime = datetime.fromisoformat(start_time)
        time_min = (start_datetime - timedelta(minutes=1)).isoformat() + "Z"
        time_max = (start_datetime + timedelta(minutes=1)).isoformat() + "Z"
        start_time_z = (start_datetime).isoformat() +"Z"

        print("Ya entró")
        print(start_time_z)

        events = get_google_calendar_events(creds,time_min, time_max)
        print(events)
        # Buscar el evento que coincide con el título y la hora de inicio
        for event in events:
            if event['summary'] == event_title and event['start']['dateTime'] == start_time_z:
                # Eliminar el evento
                service.events().delete(
                    calendarId='c_5429309c7c93803f3c31f144ef187db179ada2d6ad3d527aba230d3293704913@group.calendar.google.com',
                    eventId=event['id']
                ).execute()

                print(f"Evento eliminado: {event.get('summary')} - {event.get('start')['dateTime']}")
                return {"status": "success", "message": "Evento eliminado con éxito."}

        # Si no se encuentra ningún evento
        print(f"No se encontró un evento con el título '{event_title}' y la hora de inicio '{start_time_z}'.")
        return {"status": "not_found", "message": f"No se encontró un evento con el título '{event_title}' y la hora de inicio '{start_time_z}'."}

    except Exception as e:
        print(f"Error al eliminar el evento: {str(e)}")
        return {"status": "error", "message": str(e)}

