import random
import sys
import collections
import copy
import pygame
import board
import datetime


def load_image(title):
    image = pygame.image.load(title)
    return image


class Block(object):
    def __init__(self, row, col, color):
        self.row = row
        self.col = col
        self.color = color

    def __eq__(self, other):
        return self.row == other.row and self.col == other.col

    def __str__(self):
        return '({}, {})'.format(self.row, self.col)


class Board(object):
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.landed = []

    def has_landed(self, piece):
        for block in piece.blocks():
            if block.row == self.rows - 1:
                return True

            if self.block_at(block.row + 1, block.col):
                return True

        return False

    def land(self, piece):
        for b in piece.blocks():
            self.landed.append(b)

    def can_move(self, piece, direction):
        p = copy.deepcopy(piece)
        p.move(direction)
        return self.has_valid_position(p)

    def can_rotate(self, piece, ccw=False):
        p = copy.deepcopy(piece)
        p.rotate(ccw)
        return self.has_valid_position(p)

    def remove_lines(self):
        lines = 0
        row = self.rows - 1

        while row >= 0:
            found = True

            for col in range(0, self.cols):
                if not self.block_at(row, col):
                    found = False
                    break

            if found:
                lines += 1

                for col in range(0, self.cols):
                    self.del_block_at(row, col)

                for col in range(0, self.cols):
                    for r in range(row - 1, -1, -1):

                        flag_of_t = self.block_at(r, col)
                        if flag_of_t:
                            flag_of_t.row += 1
                row += 1
            else:
                row -= 1

        return lines

    def has_valid_position(self, piece):
        for b in piece.blocks():
            if b.row < 0 or b.row >= self.rows or b.col < 0 or b.col >= self.cols or self.block_at(b.row, b.col):
                return False
        return True

    def block_at(self, row, col):
        for b in self.landed:
            if b.row == row and b.col == col:
                return b

    def del_block_at(self, row, col):
        for i in range(len(self.landed)):
            b = self.landed[i]
            if b.row == row and b.col == col:
                self.landed.pop(i)
                break


class State(object):
    def __init__(self, rows, cols):
        self.board = board.Board(rows, cols)
        self.score = 0
        self.piece = None
        self.shapes = []
        self.elapsed = 0
        self.level = -1
        self.speed = 0
        self.paused = False
        self.game_over = False
        self.next_level()
        self.next_figure()

    def next_figure(self):
        shape = self.next_shape()
        self.shapes.remove(shape)
        row = col = 0
        if shape in (board.SHAPE_I, board.SHAPE_O):
            col = self.board.cols / 2
        self.piece = board.Piece(shape, row, col)

    def next_shape(self):
        if not self.shapes:
            self.shapes = list(board.ALL_SHAPES)
            random.shuffle(self.shapes)
        return self.shapes[0]

    def move_piece(self, direction):
        if self.board.can_move(self.piece, direction):
            self.piece.move(direction)

    def drop_piece(self):
        while not self.board.has_landed(self.piece):
            self.move_piece(board.DIRECTION_DOWN)

    def rotate_piece(self, ccw=False):
        if self.board.can_rotate(self.piece, ccw):
            self.piece.rotate(ccw)

    def update(self, dt):
        if self.game_over or self.paused:
            return
        self.elapsed += dt
        if self.elapsed >= self.speed:
            if not self.board.has_landed(self.piece):
                self.move_piece(board.DIRECTION_DOWN)
                self.elapsed = 0
        if self.board.has_landed(self.piece):
            self.board.land(self.piece)
            self.next_figure()
        lines = self.board.remove_lines()
        if lines:
            self.update_score(lines)
            if self.score % 200 == 0 and self.level < 9:
                self.next_level()
        for c in range(self.board.cols):
            if self.board.block_at(0, c):
                self.game_over = True

    POINTS_PER_LINES = {1: 100, 2: 200, 3: 300, 4: 1000}

    def update_score(self, lines):
        self.score += self.POINTS_PER_LINES.get(lines) * (self.level + 1)

    def next_level(self):
        self.level += 1
        self.speed = 200 - self.level * 20

    def running(self):
        return not (self.paused or self.game_over)


class Game(object):
    ROWS = 20
    COLS = 10

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.f = True
        self.ss = True

        self.state = State(self.ROWS, self.COLS)
        self.block_size = height / self.state.board.rows

        self.board_width = self.block_size * self.state.board.cols
        self.board_height = self.block_size * self.state.board.rows
        self.screen = pygame.display.set_mode((width, height))

        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 16)
        self.font.set_bold(True)

        self.text_color = pygame.Color('purple')
        self.background_color = pygame.Color('black')

    def draw_block(self, block):
        x = block.col * self.block_size
        y = block.row * self.block_size
        pygame.draw.rect(self.screen, block.color,
                         (x, y, self.block_size, self.block_size))

    def draw_text(self, text, y):
        w, h = self.font.size(text)
        x = self.board_width + (self.width - self.board_width - w) / 2
        text_surface = self.font.render(text, 1, self.text_color)
        self.screen.blit(text_surface, (x, y))

    def draw_piece(self, piece):
        for b in piece.blocks():
            self.draw_block(b)

    def draw_next_piece(self, y):
        x = self.board_width + \
            (self.width - self.board_width - self.block_size) / 2
        row = y / self.block_size
        col = x / self.block_size - 1
        piece = board.Piece(self.state.next_shape(), row, col)
        pygame.draw.rect(self.screen, piece.shape.color,
                         (x - self.block_size * 2, y - self.block_size / 2,
                          self.block_size * 5, self.block_size * 4), 1)
        self.draw_piece(piece)

    def draw_background(self):
        self.screen.fill(self.background_color)
        pygame.draw.rect(self.screen, self.text_color,
                         (0, 0, self.board_width, self.board_height), 1)
        for b in self.state.board.landed:
            self.draw_block(b)

    def input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if self.state.paused:
                    if event.key == pygame.K_r:
                        self.state.paused = False
                if self.state.game_over:
                    if event.key == pygame.K_r:
                        self.state = State(self.ROWS, self.COLS)
                        self.f = True
                    if event.key == pygame.K_ESCAPE:
                        sys.exit()
                if self.state.running:
                    if event.key == pygame.K_DOWN:
                        self.state.move_piece(board.DIRECTION_DOWN)
                    if event.key == pygame.K_LEFT:
                        self.state.move_piece(board.DIRECTION_LEFT)
                    if event.key == pygame.K_RIGHT:
                        self.state.move_piece(board.DIRECTION_RIGHT)
                    if event.key == pygame.K_x:
                        self.state.rotate_piece()
                    if event.key == pygame.K_z:
                        self.state.rotate_piece(True)
                    if event.key == pygame.K_SPACE:
                        self.state.drop_piece()
                    if event.key == pygame.K_p:
                        self.state.paused = True

    def update(self):
        if self.state.running:
            self.state.update(self.clock.get_time())

    def draw_all(self):
        self.draw_background()
        self.draw_piece(self.state.piece)
        self.draw_text('Уровень:', self.block_size)
        self.draw_text('%d' % (self.state.level + 1), self.block_size * 2)
        self.draw_text('Очки:', self.block_size * 3)
        self.draw_text('%d' % self.state.score, self.block_size * 4)
        self.draw_text('Следующая фигура:', self.block_size * 5)
        self.draw_next_piece(self.block_size * 6)
        if self.state.paused:
            self.draw_text('Игра на паузе', self.block_size * 10)
            self.draw_text('Нажмите r для продолжения', self.block_size * 11)
        if self.state.game_over:
            if self.f:
                now = str(datetime.datetime.now())
                file = open("results.txt", encoding='utf-8', mode='a')
                file.write(now + '  ---  ' + str(self.state.score) + '\n')
                file.close()
                self.f = False
            self.draw_text('Вы проиграли', self.block_size * 10)
            self.draw_text('Нажмите r для рестарта', self.block_size * 11)

        pygame.display.flip()
        self.clock.tick(60)

    def terminate(self):
        pygame.quit()
        sys.exit()

    def start_screen(self):
        intro_text = ["ИГРА В ТЕТРИС", "",
                      "Для продолжения нажмите на любую",
                      "кнопку."]

        fon = pygame.transform.scale(load_image('tetris.jpg'), (700, 500))
        self.screen.blit(fon, (0, 0))
        font = pygame.font.Font(None, 50)
        text_coord = 50
        for line in intro_text:
            string_rendered = font.render(line, 1, pygame.Color('white'))
            intro_rect = string_rendered.get_rect()
            text_coord += 10
            intro_rect.top = text_coord
            intro_rect.x = 10
            text_coord += intro_rect.height
            self.screen.blit(string_rendered, intro_rect)

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.terminate()
                elif event.type == pygame.KEYDOWN or \
                        event.type == pygame.MOUSEBUTTONDOWN:
                    self.ss = False
                    return  # начинаем игру
            pygame.display.flip()
            self.clock.tick(100)

    def run(self):
        while True:
            self.input()
            self.update()
            self.draw_all()


class Figure(object):
    def __init__(self, shape, row=0, col=0, rot=0):
        self.shape = shape
        self.row = row
        self.col = col
        self.rotation = rot

    def blocks(self):
        blocks = []
        block_x, row, col = 0x8000, 0, 0
        while block_x > 0:
            if self.shape.blocks[self.rotation] & block_x:
                blocks.append(Block(self.row + row, self.col + col, self.shape.color))

            if col == 3:
                col = 0
                row += 1
            else:
                col += 1

            block_x >>= 1

        return blocks

    def position(self):
        return self.row, self.col

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN or \
                        event.type == pygame.MOUSEBUTTONDOWN:
                    return  # начинаем игру
            pygame.display.flip()

    def move(self, direction):
        self.row += direction.delta_row
        self.col += direction.delta_col

    def rotate(self, flag=False):
        if flag:
            d = -1
        else:
            d = 1

        self.rotation = (self.rotation + d) % len(self.shape.blocks)


Direction = collections.namedtuple('Direction', ['delta_row', 'delta_col'])
DIRECTION_DOWN = Direction(delta_row=1, delta_col=0)
DIRECTION_LEFT = Direction(delta_row=0, delta_col=-1)
DIRECTION_RIGHT = Direction(delta_row=0, delta_col=1)
ALL_DIRECTIONS = (DIRECTION_DOWN, DIRECTION_LEFT, DIRECTION_RIGHT)


if __name__ == '__main__':
    pygame.init()
    pygame.display.set_caption('Игра в тетрис')
    game = Game(700, 500)
    while game.ss:
        game.start_screen()
    else:
        game.run()
