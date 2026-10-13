"""Kolory i arkusze stylów (QSS – odpowiednik CSS dla Qt)."""

# Klasyczna paleta Va banque.
NAVY = "#0b1a4a"  # tło
BOARD_BLUE = "#1d3fb3"  # pola planszy
GOLD = "#f2c94c"  # wartości i akcenty
WHITE = "#ffffff"

MENU_STYLE = f"""
#MenuScreen {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #142a6e, stop:1 {NAVY});
}}
#MenuTitle {{
    color: {GOLD};
    font-size: 64pt;
    font-weight: bold;
}}
#MenuSubtitle {{
    color: #c9d4f5;
    font-size: 16pt;
}}
#MenuInfo {{
    color: #8fa3dc;
    font-size: 11pt;
}}
#MenuScreen QPushButton {{
    background: {BOARD_BLUE};
    color: {WHITE};
    border: 2px solid #3a5fd6;
    border-radius: 10px;
    padding: 12px;
    font-size: 17pt;
    font-weight: bold;
}}
#MenuScreen QPushButton:hover, #MenuScreen QPushButton:focus {{
    border-color: {GOLD};
    color: {GOLD};
}}
#MenuScreen QPushButton:disabled {{
    background: #1a2a5c;
    color: #5d6c99;
    border-color: #26386e;
}}
"""
