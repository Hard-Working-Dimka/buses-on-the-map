import json


def validate_browser_response(response: str):
    errors = []

    try:
        response = json.loads(response)
    except json.JSONDecodeError:
        errors.append('Requires valid JSON')
        return {'valid': False, 'errors': errors}

    msg_type = response.get('msgType')
    if msg_type is None:
        errors.append('[msgType] --- You forgot to specify the message type or put it in the wrong place!')
    elif not isinstance(msg_type, str):
        errors.append('[msgType] --- The type is incorrect, it must be a string.')

    coords = response.get('data')

    if coords is None:
        errors.append('[data] --- You forgot to specify the data or put it in the wrong place!')
    elif not isinstance(coords, dict):
        errors.append('[data] --- Data must be an object with coordinates!')
    else:

        required_fields = ['south_lat', 'north_lat', 'west_lng', 'east_lng']
        for field in required_fields:
            if field not in coords:
                errors.append(f'[data.{field}] --- Missing required field!')
            else:
                val = coords[field]
                if not isinstance(val, float):
                    errors.append(f'[data.{field}] --- Invalid type: expected float.')

    if errors:
        return {'valid': False, 'errors': errors}
    return {'valid': True, 'errors': []}


def validate_bus_response(response: str):
    errors = []

    try:
        response = json.loads(response)
    except json.JSONDecodeError:
        errors.append('Requires valid JSON')
        return {'valid': False, 'errors': errors}

    if not isinstance(response, dict):
        errors.append('Requires valid JSON')

    bus_id = response.get('busId')
    if bus_id is None:
        errors.append('[busId] --- You forgot to specify the busId or put it in the wrong place!')
    elif not isinstance(bus_id, str):
        errors.append(f'[busId] --- The type is incorrect, it must be a string.')

    lat = response.get('lat')
    if lat is None:
        errors.append('[lat] --- You forgot to specify the latitude!')
    elif not isinstance(lat, float):
        errors.append(f'[lat] --- The type is incorrect, it must be float.')

    lng = response.get('lng')
    if lng is None:
        errors.append('[lng] --- You forgot to specify the longitude!')
    elif not isinstance(lng, float):
        errors.append(f'[lng] --- The type is incorrect, it must be float.')

    route = response.get('route')
    if not route:
        errors.append('[route] --- You forgot to specify the route or put it in the wrong place!')
    elif not isinstance(route, str):
        errors.append(f'[route] --- The type is incorrect, it must be a string.')

    if errors:
        return {'valid': False, 'errors': errors}
    return {'valid': True, 'errors': []}
