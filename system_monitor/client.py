from ctypes import *
from sdl2 import *
from sdl2.sdlttf import *
import sdl2.ext

import json, socket, struct, decimal
from pprint import pprint

# text color: white
fg = SDL_Color(255,0,0)
 
# bgcolor: black
bg = SDL_Color(0,0,0)

window_width  = 1920
window_height = 1080

# ==============================================
def round(value, places = 1):
    return decimal.Decimal(str(value)).quantize(decimal.Decimal('1e-' + str(places)))

# ==============================================
def render_text(text):
    # render text into surface
    #surface = TTF_RenderText_Solid(font, b"Hello world!", fg)
    #surface = TTF_RenderText_Shaded(font, b"Hello world!", fg, bg)
    surface = TTF_RenderText_Blended(font, text.encode(), fg)
     
    # create texture from surface
    texture = SDL_CreateTextureFromSurface(renderer, surface)

    SDL_FreeSurface(surface)

     
    # get size of the text-texture
    texW = c_int()
    texH = c_int()
    SDL_QueryTexture(texture, None, None, byref(texW), byref(texH))

    return texture, texW, texH


# ==============================================
def heading(text):
    return {
        'type' : 'heading',
        'data' : render_text(text)
    }


# ==============================================
def render_heading(renderer, pos_x, pos_y, data):
    x_pos_base = c_int(pos_x + 10)
    y_pos_base = c_int(pos_y + 20)

    dstrect = SDL_Rect(x_pos_base, y_pos_base, data[1], data[2])

    SDL_RenderCopy(renderer, data[0], None, dstrect)


# ==============================================
def table(data):
    # Render all labels
    result = []
    for row in data:
        rendered_row = []
        for col in row:
            rendered_row.append(render_text(col))

        result.append(rendered_row)

    return {
        'type' : 'table',
        'data' : result
    }


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




# ==============================================================================
# Main client API
# ==============================================================================
stored_config = None

def init_client(config):
    global win, renderer, font, stored_config

    stored_config = config


    # Initialize SDL2
    SDL_Init(SDL_INIT_VIDEO)
     
    # Initialize SDL2_ttf
    TTF_Init()
     
    # legacy mode or OpenGL mode
    win = SDL_CreateWindow(b"Dashboard",  0,0, window_width, window_height,  SDL_WINDOW_OPENGL|SDL_WINDOW_RESIZABLE)

    # create renderer
    renderer = SDL_CreateRenderer(win, -1, 0)
     
    # load TTF font
    font = TTF_OpenFont("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf".encode(), 16)
     
    SDL_EnableScreenSaver()


# =====================================
running = True

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
connections = {}

def get_remote_data():
    global connections

    remote_data = {}

    for hostname, con_info in stored_config['hosts'].items():
        if hostname not in connections:
            s = socket.socket()        
            s.connect((con_info[0], con_info[1]))
            connections[hostname] = s

        s = connections[hostname]

        data_length = struct.unpack("!i", s.recv(4))[0]

        data = b'' 
        while len(data) != data_length:
            data += s.recv(data_length)

        remote_data[hostname]  = json.loads(data)

    return remote_data


# ==========================================
def render(display_list):
    # Clear screen
    SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
    SDL_RenderClear(renderer);

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

