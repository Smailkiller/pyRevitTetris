# -*- coding: utf-8 -*-
import clr
import os
import sys
import json
import random

clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
clr.AddReference("WindowsBase")

import System
from System.Windows.Markup import XamlReader
from System.IO import FileStream, FileMode
from System.Windows import Window, Thickness
from System.Windows.Controls import Button, Canvas, StackPanel, TextBlock, ScrollViewer, RadioButton
from System.Windows.Shapes import Rectangle, Line
from System.Windows.Media import SolidColorBrush, Colors, ImageBrush
from System.Windows.Media.Imaging import BitmapImage
from System.Windows.Threading import DispatcherTimer
from System import TimeSpan

# Параметры игрового поля
cell_size = 20
cols = 10
rows = 20
fig_w, fig_h = 5, 5

# Путь к папке скрипта
script_dir = os.path.dirname(os.path.abspath(__file__))
skins_dir = os.path.join(script_dir, "skins", "images")

def get_image_brush(skin_folder, image_index, cell_size):
    img_path = os.path.join(skins_dir, skin_folder, "{}.png".format(image_index))
    if not os.path.exists(img_path):
        print("Image file not found: {}".format(img_path))
        return None
    
    img = BitmapImage()
    img.BeginInit()
    img.UriSource = System.Uri(img_path, System.UriKind.Absolute)
    img.DecodePixelWidth = cell_size
    img.DecodePixelHeight = cell_size
    img.EndInit()

    from System.Windows.Media import ImageBrush
    brush = ImageBrush(img)
    return brush

# Файл сохранения данных пользователя (покупки, текущий скин)
save_file = os.path.join(script_dir, "tetris_save.json")
current_color_index = 0

# Палитры цветов
classic_colors = [
    Colors.Blue,
    Colors.Green,
    Colors.Red,
    Colors.Yellow,
    Colors.Cyan,
    Colors.Magenta,
    Colors.Orange
]

bw_colors = [
    Colors.DarkGray,
    Colors.Gray,
    Colors.LightGray,
    Colors.White,
    Colors.DimGray,
    Colors.Silver
]

pastel_colors = [
    Colors.LightPink,
    Colors.LightGreen,
    Colors.LightBlue,
    Colors.LightYellow,
    Colors.Plum,
    Colors.PeachPuff,
    Colors.PaleTurquoise
]

# Таблица фигур 5x5 с ротациями
figures = {
    'S': [
        ['ooooo',
         'ooooo',
         'ooxxo',
         'oxxoo',
         'ooooo'],
        ['ooooo',
         'ooxoo',
         'ooxxo',
         'oooxo',
         'ooooo']
    ],
    'Z': [
        ['ooooo',
         'ooooo',
         'oxxoo',
         'ooxxo',
         'ooooo'],
        ['ooooo',
         'ooxoo',
         'oxxoo',
         'oxooo',
         'ooooo']
    ],
    'J': [
        ['ooooo',
         'oxooo',
         'oxxxo',
         'ooooo',
         'ooooo'],
        ['ooooo',
         'ooxxo',
         'ooxoo',
         'ooxoo',
         'ooooo'],
        ['ooooo',
         'ooooo',
         'oxxxo',
         'oooxo',
         'ooooo'],
        ['ooooo',
         'ooxoo',
         'ooxoo',
         'oxxoo',
         'ooooo']
    ],
    'L': [
        ['ooooo',
         'oooxo',
         'oxxxo',
         'ooooo',
         'ooooo'],
        ['ooooo',
         'ooxoo',
         'ooxoo',
         'ooxxo',
         'ooooo'],
        ['ooooo',
         'ooooo',
         'oxxxo',
         'oxooo',
         'ooooo'],
        ['ooooo',
         'oxxoo',
         'ooxoo',
         'ooxoo',
         'ooooo']
    ],
    'I': [
        ['ooxoo',
         'ooxoo',
         'ooxoo',
         'ooxoo',
         'ooooo'],
        ['ooooo',
         'ooooo',
         'xxxxo',
         'ooooo',
         'ooooo']
    ],
    'O': [
        ['ooooo',
         'ooooo',
         'oxxoo',
         'oxxoo',
         'ooooo']
    ],
    'T': [
        ['ooooo',
         'ooxoo',
         'oxxxo',
         'ooooo',
         'ooooo'],
        ['ooooo',
         'ooxoo',
         'ooxxo',
         'ooxoo',
         'ooooo'],
        ['ooooo',
         'ooooo',
         'oxxxo',
         'ooxoo',
         'ooooo'],
        ['ooooo',
         'ooxoo',
         'oxxoo',
         'ooxoo',
         'ooooo']
    ]
}

# Скины и палитры
skins = [
    {
        "name": "Классика",
        "type": "colors",
        "colors": classic_colors,
        "purchased": True,
        "price": 0
    },
    {
        "name": "Ч/Б",
        "type": "colors",
        "colors": bw_colors,
        "purchased": False,
        "price": 20
    },
    {
        "name": "Пастель",
        "type": "colors",
        "colors": pastel_colors,
        "purchased": False,
        "price": 40
    },
    {
        "name": "Картинки #1",
        "type": "images",
        "folder": "images1",
        "purchased": False,
        "price": 100
    },
    {
        "name": "Картинки #2",
        "type": "images",
        "folder": "images2",
        "purchased": False,
        "price": 150
    }
]

current_skin_index = 0  # классика по умолчанию

# Загрузка XAML
xaml_path = os.path.join(script_dir, "tetris_ui.xaml")
stream = FileStream(xaml_path, FileMode.Open)
window = XamlReader.Load(stream)
stream.Close()

# Находим элементы
game_canvas = window.FindName("GameCanvas")
score_text = window.FindName("ScoreText")
exit_button = window.FindName("ExitButton")
pause_button = window.FindName("PauseButton")
shop_button = window.FindName("ShopButton") if window.FindName("ShopButton") else None

# Игровое поле (2D список)
field = [[None for _ in range(rows)] for _ in range(cols)]

# Текущая фигура
current_shape = None
current_rotation = 0
current_x = 0
current_y = 0

score = 0
is_paused = False
shop_window = None  # глобально для окна магазина

# --- Функции сохранения и загрузки ---
def load_save():
    global current_skin_index, score
    try:
        with open(save_file, "r") as f:
            data = json.load(f)
            current_skin_index = data.get("current_skin_index", 0)
            score = data.get("score", 0)
            purchased = data.get("purchased_skins", {})
            for i, skin in enumerate(skins):
                skin["purchased"] = purchased.get(str(i), skin["purchased"])
    except:
        pass

def save_state():
    data = {
        "current_skin_index": current_skin_index,
        "score": score,
        "purchased_skins": {str(i): skin["purchased"] for i, skin in enumerate(skins)}
    }
    try:
        with open(save_file, "w") as f:
            json.dump(data, f)
    except:
        pass

# --- Рисуем сетку ---
def draw_grid():
    to_remove = []
    for child in game_canvas.Children:
        if isinstance(child, Line):
            to_remove.append(child)
    for child in to_remove:
        game_canvas.Children.Remove(child)
    for i in range(cols + 1):
        x = i * cell_size
        line = Line()
        line.Stroke = SolidColorBrush(Colors.Gray)
        line.X1 = x
        line.Y1 = 0
        line.X2 = x
        line.Y2 = rows * cell_size
        game_canvas.Children.Add(line)
    for j in range(rows + 1):
        y = j * cell_size
        line = Line()
        line.Stroke = SolidColorBrush(Colors.Gray)
        line.X1 = 0
        line.Y1 = y
        line.X2 = cols * cell_size
        line.Y2 = y
        game_canvas.Children.Add(line)

# --- Рисуем поле и фигуры ---
def draw_field():
    # Удаляем все старые прямоугольники и изображения
    to_remove = []
    for child in game_canvas.Children:
        if isinstance(child, Rectangle) or hasattr(child, "Source"):
            to_remove.append(child)
    for child in to_remove:
        game_canvas.Children.Remove(child)

    skin = skins[current_skin_index]

    # Рисуем уже закрепленные блоки на поле
    for x in range(cols):
        for y in range(rows):
            color_idx = field[x][y]
            if color_idx is not None:
                draw_block(x, y, color_idx)

    # Рисуем текущую падающую фигуру с одним цветом/скином
    if current_shape is not None:
        fig_data = figures[current_shape][current_rotation]
        for fx in range(fig_w):
            for fy in range(fig_h):
                if fig_data[fy][fx] == 'x':
                    px = current_x + fx
                    py = current_y + fy
                    if py >= 0:
                        draw_block(px, py, current_color_index)

# --- Рисуем один блок с учётом скина ---
def draw_block(x, y, color_idx):
    skin = skins[current_skin_index]
    if skin["type"] == "colors":
        rect = Rectangle()
        rect.Width = cell_size - 1
        rect.Height = cell_size - 1
        rect.Fill = SolidColorBrush(skin["colors"][color_idx])
        game_canvas.Children.Add(rect)
        from System.Windows.Controls import Canvas as C
        C.SetLeft(rect, x * cell_size)
        C.SetTop(rect, y * cell_size)
    elif skin["type"] == "images":
        brush = get_image_brush(skin["folder"], color_idx + 1, cell_size)
        rect = Rectangle()
        rect.Width = cell_size - 1
        rect.Height = cell_size - 1
        if brush is not None:
            rect.Fill = brush
        else:
            rect.Fill = SolidColorBrush(Colors.Red)  # Ошибка загрузки картинки
        game_canvas.Children.Add(rect)
        from System.Windows.Controls import Canvas as C
        C.SetLeft(rect, x * cell_size)
        C.SetTop(rect, y * cell_size)

# --- Проверка коллизии фигуры ---
def can_place(x, y, shape, rotation):
    fig_data = figures[shape][rotation]
    for fx in range(fig_w):
        for fy in range(fig_h):
            if fig_data[fy][fx] == 'x':
                px = x + fx
                py = y + fy
                if px < 0 or px >= cols or py >= rows:
                    return False
                if py >= 0 and field[px][py] is not None:
                    return False
    return True

# --- Добавление фигуры в поле ---
def place_figure():
    global field
    fig_data = figures[current_shape][current_rotation]
    for fx in range(fig_w):
        for fy in range(fig_h):
            if fig_data[fy][fx] == 'x':
                px = current_x + fx
                py = current_y + fy
                if py >= 0:
                    # Просто сохраняем current_color_index для каждого блока
                    field[px][py] = current_color_index


# --- Очистка заполненных линий ---
def clear_lines():
    global score
    full_lines = []
    for y in range(rows):
        if all(field[x][y] is not None for x in range(cols)):
            full_lines.append(y)
    for line in full_lines:
        for y in range(line, 0, -1):
            for x in range(cols):
                field[x][y] = field[x][y - 1]
        for x in range(cols):
            field[x][0] = None
    score += len(full_lines)
    if full_lines:
        update_score()

def update_score():
    score_text.Text = "Score: {}".format(score)

# --- Создание новой фигуры ---
def new_figure():
    global current_x, current_y, current_shape, current_rotation, current_color_index
    current_shape = random.choice(list(figures.keys()))
    current_rotation = 0
    current_x = cols // 2 - fig_w // 2
    current_y = -2
    # Выбираем цвет для фигуры — индекс цвета из палитры
    skin = skins[current_skin_index]
    if skin["type"] == "colors":
        current_color_index = random.randint(0, len(skin["colors"]) - 1)
    else:
        # Для картинок просто берем индекс от 0 до 6 (7 картинок)
        current_color_index = random.randint(0, 6)

# --- Обработчик таймера (падение фигуры) ---
def on_tick(sender, e):
    global current_y
    if is_paused:
        return
    if can_place(current_x, current_y + 1, current_shape, current_rotation):
        current_y += 1
    else:
        place_figure()
        clear_lines()
        new_figure()
        if not can_place(current_x, current_y, current_shape, current_rotation):
            timer.Stop()
            System.Windows.MessageBox.Show("Game Over! Ваш счёт: {}".format(score))
            save_state()
            window.Close()
            return
    draw_field()

# --- Обработка нажатий клавиш ---
def on_key_down(sender, e):
    global current_x, current_y, current_rotation
    if is_paused:
        return
    key = e.Key.ToString()
    if key == "Left":
        if can_place(current_x - 1, current_y, current_shape, current_rotation):
            current_x -= 1
    elif key == "Right":
        if can_place(current_x + 1, current_y, current_shape, current_rotation):
            current_x += 1
    elif key == "Down":
        if can_place(current_x, current_y + 1, current_shape, current_rotation):
            current_y += 1
    elif key == "Up":
        new_rot = (current_rotation + 1) % len(figures[current_shape])
        if can_place(current_x, current_y, current_shape, new_rot):
            current_rotation = new_rot
    elif key == "Escape":
        timer.Stop()
        save_state()
        window.Close()
    draw_field()

# --- Обработчик кнопки выхода ---
def on_exit(sender, e):
    timer.Stop()
    save_state()
    window.Close()

exit_button.Click += on_exit

# --- Обработчик кнопки паузы ---
def on_pause(sender, e):
    global is_paused
    if is_paused:
        is_paused = False
        pause_button.Content = "Пауза"
        timer.Start()
    else:
        is_paused = True
        pause_button.Content = "Продолжить"
        timer.Stop()

pause_button.Click += on_pause

# --- Магазин скинов ---
def open_shop(sender, e):
    global shop_window, is_paused
    is_paused = True
    timer.Stop()
    pause_button.Content = "Продолжить"

    shop_window = Window()
    shop_window.Title = "Магазин скинов"
    shop_window.Width = 320
    shop_window.Height = 450
    shop_window.WindowStartupLocation = System.Windows.WindowStartupLocation.CenterScreen
    shop_window.Background = SolidColorBrush(Colors.Black)
    shop_window.WindowStyle = System.Windows.WindowStyle.None
    shop_window.ResizeMode = System.Windows.ResizeMode.NoResize

    scroll = ScrollViewer()
    stack = StackPanel()
    scroll.Content = stack
    shop_window.Content = scroll

    def buy_skin(index):
        global score
        skin = skins[index]
        if not skin["purchased"]:
            price = skin["price"]
            if score >= price:
                score -= price
                skin["purchased"] = True
                update_score()  # обновляем текст с очками
                save_state()
                build_shop_ui()
            else:
                System.Windows.MessageBox.Show("Недостаточно очков для покупки этого скина.")

    def select_skin(index):
        global current_skin_index
        current_skin_index = index
        save_state()
        new_figure()
        draw_field()
        build_shop_ui()

    def build_shop_ui():
        stack.Children.Clear()
        for i, skin in enumerate(skins):
            sp = StackPanel()
            sp.Orientation = System.Windows.Controls.Orientation.Horizontal
            name_tb = TextBlock()
            name_tb.Text = skin["name"]
            name_tb.Width = 120
            name_tb.Foreground = SolidColorBrush(Colors.White)  # Добавляем цвет текста
            name_tb.FontSize = 14  # По желанию увеличить шрифт
            sp.Children.Add(name_tb)

            if skin["purchased"]:
                rb = RadioButton()
                rb.GroupName = "skins"
                rb.IsChecked = (current_skin_index == i)
                rb.Checked += lambda s, e, idx=i: select_skin(idx)
                sp.Children.Add(rb)
            else:
                btn = Button()
                btn.Content = "Buy for {}".format(skin["price"])
                btn.IsEnabled = score >= skin["price"]
                btn.Click += lambda s, e, idx=i: buy_skin(idx)
                sp.Children.Add(btn)

            stack.Children.Add(sp)

        # Кнопка закрыть магазин
        close_btn = Button()
        close_btn.Content = "Закрыть"
        close_btn.Height = 30
        close_btn.Margin = Thickness(5)
        close_btn.Click += close_shop
        stack.Children.Add(close_btn)

    def close_shop(sender, e):
        global shop_window, is_paused
        if shop_window:
            shop_window.Close()
            shop_window = None
        is_paused = False
        pause_button.Content = "Пауза"
        timer.Start()

    build_shop_ui()
    shop_window.ShowDialog()

if shop_button:
    shop_button.Click += open_shop

# --- Загрузка состояния ---
load_save()

# --- Инициализация ---
draw_grid()
new_figure()
update_score()
draw_field()

# --- Таймер ---
timer = DispatcherTimer()
timer.Interval = TimeSpan.FromMilliseconds(500)
timer.Tick += on_tick
timer.Start()

# --- Клавиши ---
window.KeyDown += on_key_down

# --- Запуск ---
window.ShowDialog()
