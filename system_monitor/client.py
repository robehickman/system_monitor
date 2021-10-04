import sys, copy, time, decimal
import json, socket, struct 

from threading import Thread, Lock

from ctypes import *
from sdl2 import *
from sdl2.sdlttf import *
import sdl2.ext


# text color
fg_normal = None
fg_error  = None

# background color
bg = None

window_width  = 1920
window_height = 1080

# ==================
stored_config = None
pool = []

# ==============================================
def round(value, places = 1):
    return decimal.Decimal(str(value)).quantize(decimal.Decimal('1e-' + str(places)))

# ==============================================
def render_text(text, color):

    col = fg_normal

    if color == 'error':
        col = fg_error

    surface = TTF_RenderText_Blended(font, text.encode(), col)
    texture = SDL_CreateTextureFromSurface(renderer, surface)
    SDL_FreeSurface(surface)

    # get size of the text-texture
    texW = c_int()
    texH = c_int()
    SDL_QueryTexture(texture, None, None, byref(texW), byref(texH))

    return texture, texW, texH



# ==============================================
def render_heading(renderer, pos_x, pos_y, data):
    x_pos_base = c_int(pos_x + 10)
    y_pos_base = c_int(pos_y + 20)

    dstrect = SDL_Rect(x_pos_base, y_pos_base, data[1], data[2])

    SDL_RenderCopy(renderer, data[0], None, dstrect)




# ==============================================
def table_row_heights(data):
    row_heights = []
    for row in data:
        row_heights.append(max([x[2].value for x in row]))

    return row_heights


# ==============================================
def table_col_widths(data):
    col_widths = []
    for col_idx in range(0, len(data[0])):
        col_widths.append(max([row[col_idx][1].value for row in data]))

    return col_widths


# ==============================================
def render_table(renderer, pos_x, pos_y, data):
    #find the tallest element for each row
    row_heights = table_row_heights(data)

    #find the widest element in each column
    col_widths = table_col_widths(data)

    # draw and position values relative to longest label so they align properly
    for row_idx in range(0, len(data)):
        for col_idx in range(0, len(data[row_idx])):

            x_pos_base = c_int(pos_x + (sum(col_widths[0:col_idx]) + (20 * col_idx)) + 20)
            y_pos_base = c_int(pos_y + (sum(row_heights[0:row_idx]) + 20))

            dstrect = SDL_Rect(x_pos_base, y_pos_base, data[row_idx][col_idx][1], data[row_idx][col_idx][2])

            SDL_RenderCopy(renderer, data[row_idx][col_idx][0], None, dstrect)


# ==========================================
def render_display_list(display_list, pos_x = 0, pos_y = 0):
    for item in display_list:
        if item['type'] == 'vertical_stack':
            y_offset = pos_y

            for it in item['data']:
                render_display_list([it], pos_x, y_offset)

                if it['type'] == 'table':
                    y_offset += sum(table_row_heights(it['data']))

                if it['type'] == 'heading':
                    y_offset += it['data'][2].value

                # add padding between items
                y_offset += 20

        elif item['type'] == 'horizontal_stack':
            col_width = window_width / len(item['data'])

            i = 0
            for it in item['data']:
                render_display_list([it], int(col_width * i), pos_y)
                i += 1

        elif item['type'] == 'heading':
            render_heading(renderer, pos_x, pos_y, item['data'])

        elif item['type'] == 'table':
            render_table(renderer, pos_x, pos_y, item['data'])


# ==========================================
def free_display_list(display_list):

    for item in display_list:

        if item['type'] == 'vertical_stack':
            for it in item['data']:
                free_display_list([it])

        elif item['type'] == 'horizontal_stack':
            for it in item['data']:
                free_display_list([it])

        elif item['type'] == 'heading':
            SDL_DestroyTexture(item['data'][0])

        elif item['type'] == 'table':
            for row in item['data']:
                for col in row:
                    SDL_DestroyTexture(col[0])



# ==========================================
running           = True

def shutdown_handler(exctype, value, traceback):
    global running
    if exctype == KeyboardInterrupt:
        running = False
    else:
        sys.__excepthook__(exctype, value, traceback)
sys.excepthook = shutdown_handler

# ==========================================
remote_data_cache = {}
threadLock        = Lock()

def server_connection_handler(hostname, con_info):
    global running, remote_data_cache, threadLock

    while running:
        try:
            s = socket.socket()
            s.settimeout(5)

            s.connect((con_info[0], con_info[1]))

            print('connected to ' + hostname)

            while running:
                data_length = struct.unpack("!i", s.recv(4))[0]

                data = b''
                while len(data) != data_length:
                    data += s.recv(data_length)

                data = json.loads(data)

                with threadLock:
                    remote_data_cache[hostname] = data

        except KeyboardInterrupt:
            return

        except Exception as e:
            with threadLock:
                try:
                    remote_data_cache.pop(hostname)
                except KeyError:
                    pass

            print('lost connection to ' + hostname + ', waiting to reconect' )

            time.sleep(10)


# ==============================================================================
# Main client API
# ==============================================================================

def init_client(config):
    global fg_normal, fg_error, bg, win, renderer, font, stored_config, pool

    stored_config = config

    # ----------
    if 'fg_normal' in config:
        fg_normal = SDL_Color(config['fg_normal'][0], config['fg_normal'][1], config['fg_normal'][2])
    else:
        fg_normal = SDL_Color(131, 149, 199)

    # ----------
    if 'fg_error' in config:
        fg_error = SDL_Color(config['fg_error'][0], config['fg_error'][1], config['fg_error'][2])
    else:
        fg_error = SDL_Color(255, 0, 0)

    # ----------
    if 'bg' in config:
        bg = SDL_Color(config['bg'][0], config['bg'][1], config['bg'][2])
    else:
        bg = SDL_Color(10,10,10)


    # Initialize SDL2
    SDL_Init(SDL_INIT_VIDEO)
    SDL_EnableScreenSaver()

    # Initialize SDL2_ttf
    TTF_Init()

    # legacy mode or OpenGL mode
    win = SDL_CreateWindow(b"Dashboard",  0,0, window_width, window_height,  SDL_WINDOW_OPENGL|SDL_WINDOW_RESIZABLE)

    # create renderer
    renderer = SDL_CreateRenderer(win, -1, 0)

    # load TTF font
    font = TTF_OpenFont("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf".encode(), 16)

    # ====================
    for hostname, con_info in stored_config['hosts'].items():
        pool.append(
            Thread(target=server_connection_handler,
                args=(hostname, con_info)))

    [t.start() for t in pool]


# =====================================
def client_active():
    global running, window_width, window_height

    events = sdl2.ext.get_events()
    for event in events:
        if event.type == sdl2.SDL_QUIT:
            running = False
            break

        if event.type == sdl2.SDL_WINDOWEVENT:
            try:
                if event.window.event == sdl2.SDL_WINDOWEVENT_RESIZED :
                    window_width  = event.window.data1
                    window_height = event.window.data2
                    SDL_SetWindowSize(window, window_width, window_height)
            except:
                pass

    return running

# =====================================
def get_remote_data():
    global remote_data_cache, threadLock

    data = None

    with threadLock:
        data = copy.deepcopy(remote_data_cache)

    return data


# ==========================================
def render(display_list):
    # Clear screen
    SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255)
    SDL_RenderClear(renderer)

    render_display_list(display_list)

    SDL_RenderPresent(renderer)

    free_display_list(display_list)

# ==========================================
def close_client():
    TTF_CloseFont(font)
    SDL_DestroyRenderer(renderer)
    SDL_DestroyWindow(win)
    TTF_Quit()
    SDL_Quit()

# ==============================================================================
# Client GUI helpers
# ==============================================================================
def horizontal_stack(data):
    return [{
        'type' : 'horizontal_stack',
        'data' : data
    }]


# ======================================
def vertical_stack(data):
    return [{
        'type' : 'vertical_stack',
        'data' : data
    }]


# ==============================================
def heading(text, color = 'normal'):
    return {
        'type'  : 'heading',
        'data'  : render_text(text, color)
    }


# ==============================================
def table(data, color = 'normal'):
    # Render all labels
    result = []
    for row in data:
        rendered_row = []
        for col in row:
            rendered_row.append(render_text(col, color))

        result.append(rendered_row)

    return {
        'type' : 'table',
        'data' : result
    }


# ======================================
def render_smart_data_block(remote_data, hostname, smart_device, device_conf):
    if hostname not in remote_data:
        return [heading('Cannot connect to ' + hostname, 'error')]

    device_data = remote_data[hostname]['smart_data'][smart_device]

    # Rudimentary error checking
    is_error = False

    if not device_data['passed']:
        is_error = True

    for attr_name in stored_config['smart_error'][hostname][smart_device]:
        if int(device_data['attrs'][attr_name]) > 0:
            is_error = True

    # =================
    output = [
        [smart_device, ('Passed' if device_data['passed'] else 'Failed')]
    ]

    for attr_name in device_conf:
        output.append([
            attr_name,
            device_data['attrs'][attr_name]
        ])

    color = 'normal' if not is_error else 'error'

    return [table(output, color)]


# ======================================
def render_disk_usage(remote_data, hostname):
    if hostname not in remote_data:
        return [heading('Cannot connect to ' + hostname, 'error')]

    res = [heading('Percentage disk used')]

    output = []
    for device, used in remote_data[hostname]['disk_use'].items():
        output.append([device + ': ', str(round(used * 100))])

    return res + [table(output)]


# ======================================
def render_memory_usage(remote_data, hostname):
    if hostname not in remote_data:
        return [heading('Cannot connect to ' + hostname, 'error')]

    return [
        table([[
            'Memory:',
            str(round(remote_data[hostname]['memory']['used'] / 1048576))  + ' MB of ' + str(round(remote_data[hostname]['memory']['available'] / 1048576)) + ' MB'
        ]])
    ]


# ======================================
def render_cpu_usage(remote_data, hostname):
    if hostname not in remote_data:
        return [heading('Cannot connect to ' + hostname, 'error')]

    res = [heading('CPU')]

    i = 1
    output = []
    for usage in remote_data[hostname]['cpu']:
        output.append([
            'cpu' + str(i) + ': ',
            str(usage)
        ])

        i += 1

    return res + [table(output)]


# ======================================
def render_network_usage(remote_data, hostname):
    if hostname not in remote_data:
        return [heading('Cannot connect to ' + hostname, 'error')]

    return [
        heading('Network'),
        table([
            [
                'Recv:',
                str(round(remote_data[hostname]['network']['recv']))
            ],
            [
                'Sent:',
                str(round(remote_data[hostname]['network']['sent']))
            ]
        ])
    ]
