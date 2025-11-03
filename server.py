import json
from functools import partial

import trio
from trio_websocket import serve_websocket, ConnectionClosed

BUSES = {}


async def talk_to_browser(request):
    ws = await request.accept()

    while True:
        try:
            buses_location = {
                "msgType": "Buses",
                "buses": [
                    {
                        "busId": bus_id,
                        "lat": bus_data['lat'],
                        "lng": bus_data['lng'],
                        "route": bus_data['route']
                    }
                    for bus_id, bus_data in BUSES.items()
                ]
            }

            buses_location = json.dumps(buses_location)
            await ws.send_message(buses_location)
            await trio.sleep(1)
        except ConnectionClosed:
            break


async def update_current_location(request):
    ws = await request.accept()
    while True:
        try:
            current_location = await ws.get_message()
            current_location = json.loads(current_location)

            BUSES[current_location['busId']] = {'busId': current_location['busId'],
                                                'lat': current_location['lat'],
                                                'lng': current_location['lng'],
                                                'route': current_location['route'],
                                                }

            print(current_location)
        except ConnectionClosed:
            break


async def main():
    serve_websocket_with_ssl_contex = partial(serve_websocket, ssl_context=None)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(serve_websocket_with_ssl_contex, update_current_location, '127.0.0.1', 8080)
        nursery.start_soon(serve_websocket_with_ssl_contex, talk_to_browser, '127.0.0.1', 8000)


trio.run(main)
