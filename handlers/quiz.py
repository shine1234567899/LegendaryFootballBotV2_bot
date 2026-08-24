from __future__ import annotations
import asyncio

import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import GameSetting, User


IMAGE_FILE = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "quiz.jpg"
)

QUIZ_REWARD = 20_000
TOTAL_QUESTIONS = 300
QUIZ_TIME_LIMIT = 20

QUIZ_LANG_KEY = "quiz_language:{user_id}"
QUIZ_ACTIVE_KEY = "quiz_active:{user_id}"
QUIZ_MESSAGE_KEY = "quiz_message:{user_id}"
QUIZ_CHAT_KEY = "quiz_chat:{user_id}"
QUIZ_DEADLINE_KEY = "quiz_deadline:{user_id}"

# One timer task per active player. asyncio is used instead of JobQueue so
# the bot does not require the optional python-telegram-bot[job-queue]
# package.
QUIZ_TIMERS = {}


# Each player has a personal history:
# quiz_seen:<user_id> = comma-separated question IDs already shown
# quiz_current:<user_id> = current question ID
#
# Once a question has been seen, it is never selected again for
# that player until the full bank has been exhausted.
#
# Wrong answer:
#   - no reward
#   - the current question is kept in the seen history
#   - a new unseen question is sent immediately
#
# Correct answer:
#   - reward
#   - current question is kept in the seen history
#   - a new unseen question is sent immediately


QUESTIONS = [
    {
        "question": "Which country won the FIFA World Cup in 1930?",
        "answers": [
            "Argentina",
            "Brazil",
            "Uruguay",
            "Germany"
        ],
        "correct": 2
    },
    {
        "question": "Which country won the FIFA World Cup in 1934?",
        "answers": [
            "Argentina",
            "Brazil",
            "Italy",
            "Germany"
        ],
        "correct": 2
    },
    {
        "question": "Which country won the FIFA World Cup in 1938?",
        "answers": [
            "Italy",
            "Germany",
            "Argentina",
            "Brazil"
        ],
        "correct": 0
    },
    {
        "question": "Which country won the FIFA World Cup in 1950?",
        "answers": [
            "Argentina",
            "Germany",
            "Uruguay",
            "Brazil"
        ],
        "correct": 2
    },
    {
        "question": "Which country won the FIFA World Cup in 1954?",
        "answers": [
            "Germany",
            "Brazil",
            "Argentina",
            "West Germany"
        ],
        "correct": 3
    },
    {
        "question": "Which country won the FIFA World Cup in 1958?",
        "answers": [
            "Germany",
            "France",
            "Brazil",
            "Argentina"
        ],
        "correct": 2
    },
    {
        "question": "Which country won the FIFA World Cup in 1962?",
        "answers": [
            "France",
            "Brazil",
            "Germany",
            "Argentina"
        ],
        "correct": 1
    },
    {
        "question": "Which country won the FIFA World Cup in 1966?",
        "answers": [
            "England",
            "Brazil",
            "Argentina",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "Which country won the FIFA World Cup in 1970?",
        "answers": [
            "Germany",
            "Brazil",
            "Argentina",
            "France"
        ],
        "correct": 1
    },
    {
        "question": "Which country won the FIFA World Cup in 1974?",
        "answers": [
            "Brazil",
            "Germany",
            "Argentina",
            "West Germany"
        ],
        "correct": 3
    },
    {
        "question": "Which country won the FIFA World Cup in 1978?",
        "answers": [
            "Germany",
            "Brazil",
            "France",
            "Argentina"
        ],
        "correct": 3
    },
    {
        "question": "Which country won the FIFA World Cup in 1982?",
        "answers": [
            "Argentina",
            "Brazil",
            "Italy",
            "Germany"
        ],
        "correct": 2
    },
    {
        "question": "Which country won the FIFA World Cup in 1986?",
        "answers": [
            "Argentina",
            "Brazil",
            "France",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "Which country won the FIFA World Cup in 1990?",
        "answers": [
            "West Germany",
            "Argentina",
            "Germany",
            "Brazil"
        ],
        "correct": 0
    },
    {
        "question": "Which country won the FIFA World Cup in 1994?",
        "answers": [
            "Brazil",
            "France",
            "Argentina",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "Which country won the FIFA World Cup in 1998?",
        "answers": [
            "Brazil",
            "France",
            "Argentina",
            "Germany"
        ],
        "correct": 1
    },
    {
        "question": "Which country won the FIFA World Cup in 2002?",
        "answers": [
            "Brazil",
            "France",
            "Argentina",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "Which country won the FIFA World Cup in 2006?",
        "answers": [
            "Italy",
            "Brazil",
            "Argentina",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "Which country won the FIFA World Cup in 2010?",
        "answers": [
            "Germany",
            "Argentina",
            "Brazil",
            "Spain"
        ],
        "correct": 3
    },
    {
        "question": "Which country won the FIFA World Cup in 2014?",
        "answers": [
            "Argentina",
            "Germany",
            "Brazil",
            "France"
        ],
        "correct": 1
    },
    {
        "question": "Which country won the FIFA World Cup in 2018?",
        "answers": [
            "Argentina",
            "Brazil",
            "Germany",
            "France"
        ],
        "correct": 3
    },
    {
        "question": "Which country won the FIFA World Cup in 2022?",
        "answers": [
            "Argentina",
            "Germany",
            "Brazil",
            "France"
        ],
        "correct": 0
    },
    {
        "question": "Which country hosted the 2014 FIFA World Cup?",
        "answers": [
            "Brazil",
            "Russia",
            "Germany",
            "South Africa"
        ],
        "correct": "Brazil"
    },
    {
        "question": "Which country hosted the 2010 FIFA World Cup?",
        "answers": [
            "South Africa",
            "Brazil",
            "Germany",
            "France"
        ],
        "correct": "South Africa"
    },
    {
        "question": "Which country hosted the 2006 FIFA World Cup?",
        "answers": [
            "Germany",
            "Italy",
            "France",
            "Spain"
        ],
        "correct": "Germany"
    },
    {
        "question": "Which country hosted the 2002 FIFA World Cup jointly?",
        "answers": [
            "Japan and South Korea",
            "China and Japan",
            "Japan and China",
            "South Korea and China"
        ],
        "correct": "Japan and South Korea"
    },
    {
        "question": "Who scored the famous 'Hand of God' goal at the 1986 World Cup?",
        "answers": [
            "Diego Maradona",
            "Pelé",
            "Zinedine Zidane",
            "Johan Cruyff"
        ],
        "correct": "Diego Maradona"
    },
    {
        "question": "Which team lost the 2010 World Cup final to Spain?",
        "answers": [
            "Netherlands",
            "Germany",
            "Italy",
            "Brazil"
        ],
        "correct": "Netherlands"
    },
    {
        "question": "Which team lost the 2014 World Cup final to Germany?",
        "answers": [
            "Argentina",
            "Brazil",
            "Netherlands",
            "France"
        ],
        "correct": "Argentina"
    },
    {
        "question": "Which team lost the 2018 World Cup final to France?",
        "answers": [
            "Croatia",
            "Belgium",
            "Argentina",
            "England"
        ],
        "correct": "Croatia"
    },
    {
        "question": "Which team lost the 2022 World Cup final to Argentina?",
        "answers": [
            "France",
            "Croatia",
            "Brazil",
            "England"
        ],
        "correct": "France"
    },
    {
        "question": "Which country won the first World Cup in 1930?",
        "answers": [
            "Uruguay",
            "Argentina",
            "Brazil",
            "Italy"
        ],
        "correct": "Uruguay"
    },
    {
        "question": "Who won the 2008 Ballon d'Or?",
        "answers": [
            "Cristiano Ronaldo",
            "Lionel Messi",
            "Kaká",
            "Xavi"
        ],
        "correct": "Cristiano Ronaldo"
    },
    {
        "question": "Who won the 2007 Ballon d'Or?",
        "answers": [
            "Kaká",
            "Cristiano Ronaldo",
            "Lionel Messi",
            "Ronaldinho"
        ],
        "correct": "Kaká"
    },
    {
        "question": "Who won the 2006 Ballon d'Or?",
        "answers": [
            "Fabio Cannavaro",
            "Ronaldinho",
            "Zinedine Zidane",
            "Andriy Shevchenko"
        ],
        "correct": "Fabio Cannavaro"
    },
    {
        "question": "Who won the 2005 Ballon d'Or?",
        "answers": [
            "Ronaldinho",
            "Lionel Messi",
            "Kaká",
            "Frank Lampard"
        ],
        "correct": "Ronaldinho"
    },
    {
        "question": "Who won the 2004 Ballon d'Or?",
        "answers": [
            "Andriy Shevchenko",
            "Pavel Nedvěd",
            "Ronaldinho",
            "Ronaldo Nazário"
        ],
        "correct": "Andriy Shevchenko"
    },
    {
        "question": "Who won the 2003 Ballon d'Or?",
        "answers": [
            "Pavel Nedvěd",
            "Zinedine Zidane",
            "Ronaldo Nazário",
            "Thierry Henry"
        ],
        "correct": "Pavel Nedvěd"
    },
    {
        "question": "Who won the 2002 Ballon d'Or?",
        "answers": [
            "Ronaldo Nazário",
            "Michael Ballack",
            "Roberto Carlos",
            "Raúl"
        ],
        "correct": "Ronaldo Nazário"
    },
    {
        "question": "Who won the 2001 Ballon d'Or?",
        "answers": [
            "Michael Owen",
            "David Beckham",
            "Luis Figo",
            "Raúl"
        ],
        "correct": "Michael Owen"
    },
    {
        "question": "Who won the 2000 Ballon d'Or?",
        "answers": [
            "Luís Figo",
            "Zinedine Zidane",
            "Rivaldo",
            "Franz Beckenbauer"
        ],
        "correct": "Luís Figo"
    },
    {
        "question": "Who won the 1999 Ballon d'Or?",
        "answers": [
            "Rivaldo",
            "David Beckham",
            "Gabriel Batistuta",
            "Ronaldo Nazário"
        ],
        "correct": "Rivaldo"
    },
    {
        "question": "Who won the 1998 Ballon d'Or?",
        "answers": [
            "Zinedine Zidane",
            "Ronaldo Nazário",
            "Davor Šuker",
            "Luís Figo"
        ],
        "correct": "Zinedine Zidane"
    },
    {
        "question": "Who won the 1997 Ballon d'Or?",
        "answers": [
            "Ronaldo Nazário",
            "Roberto Carlos",
            "Dennis Bergkamp",
            "Zinedine Zidane"
        ],
        "correct": "Ronaldo Nazário"
    },
    {
        "question": "Who won the 1996 Ballon d'Or?",
        "answers": [
            "Matthias Sammer",
            "Ronaldo Nazário",
            "Alan Shearer",
            "George Weah"
        ],
        "correct": "Matthias Sammer"
    },
    {
        "question": "Who won the 1995 Ballon d'Or?",
        "answers": [
            "George Weah",
            "Jari Litmanen",
            "Milan Baroš",
            "Romário"
        ],
        "correct": "George Weah"
    },
    {
        "question": "Who won the 1994 Ballon d'Or?",
        "answers": [
            "Hristo Stoichkov",
            "Roberto Baggio",
            "Paolo Maldini",
            "Romário"
        ],
        "correct": "Hristo Stoichkov"
    },
    {
        "question": "Who won the 1993 Ballon d'Or?",
        "answers": [
            "Roberto Baggio",
            "Dennis Bergkamp",
            "Eric Cantona",
            "Jean-Pierre Papin"
        ],
        "correct": "Roberto Baggio"
    },
    {
        "question": "Who won the 1992 Ballon d'Or?",
        "answers": [
            "Marco van Basten",
            "Dennis Bergkamp",
            "Gary Lineker",
            "Hristo Stoichkov"
        ],
        "correct": "Marco van Basten"
    },
    {
        "question": "Who won the 1991 Ballon d'Or?",
        "answers": [
            "Jean-Pierre Papin",
            "Lothar Matthäus",
            "Marco van Basten",
            "Michael Laudrup"
        ],
        "correct": "Jean-Pierre Papin"
    },
    {
        "question": "Who won the 1990 Ballon d'Or?",
        "answers": [
            "Lothar Matthäus",
            "Salvatore Schillaci",
            "Diego Maradona",
            "Andreas Brehme"
        ],
        "correct": "Lothar Matthäus"
    },
    {
        "question": "Who won the 1989 Ballon d'Or?",
        "answers": [
            "Marco van Basten",
            "Ruud Gullit",
            "Franco Baresi",
            "Roberto Baggio"
        ],
        "correct": "Marco van Basten"
    },
    {
        "question": "Which club has won the most European Cup/UEFA Champions League titles?",
        "answers": [
            "Real Madrid",
            "AC Milan",
            "Bayern Munich",
            "Liverpool"
        ],
        "correct": "Real Madrid"
    },
    {
        "question": "Which club won the 1993 UEFA Champions League?",
        "answers": [
            "Marseille",
            "AC Milan",
            "Barcelona",
            "Juventus"
        ],
        "correct": "Marseille"
    },
    {
        "question": "Which club won the 2005 UEFA Champions League final in Istanbul?",
        "answers": [
            "Liverpool",
            "AC Milan",
            "Chelsea",
            "Barcelona"
        ],
        "correct": "Liverpool"
    },
    {
        "question": "Which club won the 2012 UEFA Champions League final?",
        "answers": [
            "Chelsea",
            "Bayern Munich",
            "Real Madrid",
            "Barcelona"
        ],
        "correct": "Chelsea"
    },
    {
        "question": "Which club won the 2013 UEFA Champions League final?",
        "answers": [
            "Bayern Munich",
            "Borussia Dortmund",
            "Real Madrid",
            "Manchester United"
        ],
        "correct": "Bayern Munich"
    },
    {
        "question": "Which club won the 2014 UEFA Champions League final?",
        "answers": [
            "Real Madrid",
            "Atlético Madrid",
            "Bayern Munich",
            "Chelsea"
        ],
        "correct": "Real Madrid"
    },
    {
        "question": "Which club won the 2018 UEFA Champions League final?",
        "answers": [
            "Real Madrid",
            "Liverpool",
            "Bayern Munich",
            "Barcelona"
        ],
        "correct": "Real Madrid"
    },
    {
        "question": "Which club won the 2019 UEFA Champions League final?",
        "answers": [
            "Liverpool",
            "Tottenham Hotspur",
            "Ajax",
            "Barcelona"
        ],
        "correct": "Liverpool"
    },
    {
        "question": "Which club won the 2020 UEFA Champions League final?",
        "answers": [
            "Bayern Munich",
            "Paris Saint-Germain",
            "Liverpool",
            "Manchester City"
        ],
        "correct": "Bayern Munich"
    },
    {
        "question": "Which club won the 2021 UEFA Champions League final?",
        "answers": [
            "Chelsea",
            "Manchester City",
            "Bayern Munich",
            "Paris Saint-Germain"
        ],
        "correct": "Chelsea"
    },
    {
        "question": "Which club won the 2022 UEFA Champions League final?",
        "answers": [
            "Real Madrid",
            "Liverpool",
            "Manchester City",
            "Chelsea"
        ],
        "correct": "Real Madrid"
    },
    {
        "question": "Which club won the 2023 UEFA Champions League final?",
        "answers": [
            "Manchester City",
            "Inter Milan",
            "Real Madrid",
            "Bayern Munich"
        ],
        "correct": "Manchester City"
    },
    {
        "question": "Which club won the 2008-09 UEFA Champions League?",
        "answers": [
            "Barcelona",
            "Manchester United",
            "Chelsea",
            "Arsenal"
        ],
        "correct": "Barcelona"
    },
    {
        "question": "Which club won the 2006-07 UEFA Champions League?",
        "answers": [
            "AC Milan",
            "Liverpool",
            "Manchester United",
            "Barcelona"
        ],
        "correct": "AC Milan"
    },
    {
        "question": "Which club won the 2004-05 UEFA Champions League?",
        "answers": [
            "Liverpool",
            "AC Milan",
            "Chelsea",
            "Juventus"
        ],
        "correct": "Liverpool"
    },
    {
        "question": "Which club won the 2010-11 UEFA Champions League?",
        "answers": [
            "Barcelona",
            "Manchester United",
            "Real Madrid",
            "Inter Milan"
        ],
        "correct": "Barcelona"
    },
    {
        "question": "Which club won the 2015 UEFA Champions League final?",
        "answers": [
            "Barcelona",
            "Juventus",
            "Real Madrid",
            "Bayern Munich"
        ],
        "correct": "Barcelona"
    },
    {
        "question": "Which club won the 1999 Champions League final?",
        "answers": [
            "Manchester United",
            "Bayern Munich",
            "Real Madrid",
            "Valencia"
        ],
        "correct": "Manchester United"
    },
    {
        "question": "Which English club won the 1977 European Cup?",
        "answers": [
            "Liverpool",
            "Nottingham Forest",
            "Aston Villa",
            "Manchester United"
        ],
        "correct": "Liverpool"
    },
    {
        "question": "Which English club won the 1979 European Cup?",
        "answers": [
            "Nottingham Forest",
            "Liverpool",
            "Aston Villa",
            "Manchester United"
        ],
        "correct": "Nottingham Forest"
    },
    {
        "question": "Which English club won the 1980 European Cup?",
        "answers": [
            "Nottingham Forest",
            "Liverpool",
            "Chelsea",
            "Manchester United"
        ],
        "correct": "Nottingham Forest"
    },
    {
        "question": "Which Italian club won the 2010 Champions League?",
        "answers": [
            "Inter Milan",
            "AC Milan",
            "Juventus",
            "Roma"
        ],
        "correct": "Inter Milan"
    },
    {
        "question": "Which Spanish club won the 1992 European Cup?",
        "answers": [
            "Barcelona",
            "Real Madrid",
            "Valencia",
            "Atlético Madrid"
        ],
        "correct": "Barcelona"
    },
    {
        "question": "Which club was known as the 'Invincibles' in the 2003-04 Premier League season?",
        "answers": [
            "Arsenal",
            "Chelsea",
            "Manchester United",
            "Liverpool"
        ],
        "correct": "Arsenal"
    },
    {
        "question": "Which club won the 2010 UEFA Champions League after an Italian treble?",
        "answers": [
            "Inter Milan",
            "AC Milan",
            "Juventus",
            "Roma"
        ],
        "correct": "Inter Milan"
    },
    {
        "question": "Which club won the first Premier League title in 1992-93?",
        "answers": [
            "Manchester United",
            "Blackburn Rovers",
            "Arsenal",
            "Chelsea"
        ],
        "correct": "Manchester United"
    },
    {
        "question": "Which club won the Premier League in 1994-95?",
        "answers": [
            "Blackburn Rovers",
            "Manchester United",
            "Arsenal",
            "Newcastle United"
        ],
        "correct": "Blackburn Rovers"
    },
    {
        "question": "Which club won the 2003-04 Premier League without losing a match?",
        "answers": [
            "Arsenal",
            "Manchester United",
            "Chelsea",
            "Liverpool"
        ],
        "correct": "Arsenal"
    },
    {
        "question": "Who is nicknamed 'The Egyptian King'?",
        "answers": [
            "Mohamed Salah",
            "Riyad Mahrez",
            "Sadio Mané",
            "Didier Drogba"
        ],
        "correct": "Mohamed Salah"
    },
    {
        "question": "Which club plays home matches at Anfield?",
        "answers": [
            "Liverpool",
            "Everton",
            "Manchester City",
            "Chelsea"
        ],
        "correct": "Liverpool"
    },
    {
        "question": "Which club plays home matches at Old Trafford?",
        "answers": [
            "Manchester United",
            "Manchester City",
            "Liverpool",
            "Arsenal"
        ],
        "correct": "Manchester United"
    },
    {
        "question": "Which club plays home matches at Stamford Bridge?",
        "answers": [
            "Chelsea",
            "Fulham",
            "West Ham United",
            "Tottenham Hotspur"
        ],
        "correct": "Chelsea"
    },
    {
        "question": "Which club plays home matches at the Emirates Stadium?",
        "answers": [
            "Arsenal",
            "Tottenham Hotspur",
            "Chelsea",
            "West Ham United"
        ],
        "correct": "Arsenal"
    },
    {
        "question": "Which club plays home matches at the Etihad Stadium?",
        "answers": [
            "Manchester City",
            "Manchester United",
            "Everton",
            "Liverpool"
        ],
        "correct": "Manchester City"
    },
    {
        "question": "Which club plays home matches at Goodison Park?",
        "answers": [
            "Everton",
            "Liverpool",
            "Newcastle United",
            "West Ham United"
        ],
        "correct": "Everton"
    },
    {
        "question": "Which club is based at St James' Park?",
        "answers": [
            "Newcastle United",
            "Sunderland",
            "Aston Villa",
            "Leicester City"
        ],
        "correct": "Newcastle United"
    },
    {
        "question": "Which club is nicknamed the 'Red Devils'?",
        "answers": [
            "Manchester United",
            "Liverpool",
            "Arsenal",
            "Chelsea"
        ],
        "correct": "Manchester United"
    },
    {
        "question": "Which club is nicknamed the 'Blues' in the Premier League?",
        "answers": [
            "Chelsea",
            "Everton",
            "Manchester City",
            "Leicester City"
        ],
        "correct": "Chelsea"
    },
    {
        "question": "Which club is nicknamed the 'Gunners'?",
        "answers": [
            "Arsenal",
            "Liverpool",
            "Tottenham Hotspur",
            "West Ham United"
        ],
        "correct": "Arsenal"
    },
    {
        "question": "Which club is nicknamed the 'Reds'?",
        "answers": [
            "Liverpool",
            "Manchester United",
            "Nottingham Forest",
            "Brentford"
        ],
        "correct": "Liverpool"
    },
    {
        "question": "Which club won the Premier League in 2015-16 against the odds?",
        "answers": [
            "Leicester City",
            "Tottenham Hotspur",
            "West Ham United",
            "Everton"
        ],
        "correct": "Leicester City"
    },
    {
        "question": "Which club won the 2004-05 Premier League title?",
        "answers": [
            "Chelsea",
            "Arsenal",
            "Manchester United",
            "Liverpool"
        ],
        "correct": "Chelsea"
    },
    {
        "question": "Which club won the 2011-12 Premier League title on goal difference?",
        "answers": [
            "Manchester City",
            "Manchester United",
            "Chelsea",
            "Arsenal"
        ],
        "correct": "Manchester City"
    },
    {
        "question": "Which club won the 2013-14 Premier League title?",
        "answers": [
            "Manchester City",
            "Liverpool",
            "Chelsea",
            "Manchester United"
        ],
        "correct": "Manchester City"
    },
    {
        "question": "Which club won the 2016-17 Premier League title?",
        "answers": [
            "Chelsea",
            "Tottenham Hotspur",
            "Manchester City",
            "Arsenal"
        ],
        "correct": "Chelsea"
    },
    {
        "question": "Which club won the 2019-20 Premier League title?",
        "answers": [
            "Liverpool",
            "Manchester City",
            "Chelsea",
            "Leicester City"
        ],
        "correct": "Liverpool"
    },
    {
        "question": "Which club won the 2020-21 Premier League title?",
        "answers": [
            "Manchester City",
            "Manchester United",
            "Liverpool",
            "Chelsea"
        ],
        "correct": "Manchester City"
    },
    {
        "question": "Which club won the 2021-22 Premier League title?",
        "answers": [
            "Manchester City",
            "Liverpool",
            "Chelsea",
            "Arsenal"
        ],
        "correct": "Manchester City"
    },
    {
        "question": "Which club won the 2022-23 Premier League title?",
        "answers": [
            "Manchester City",
            "Arsenal",
            "Liverpool",
            "Manchester United"
        ],
        "correct": "Manchester City"
    },
    {
        "question": "Which club won the 2023-24 Premier League title?",
        "answers": [
            "Manchester City",
            "Arsenal",
            "Liverpool",
            "Chelsea"
        ],
        "correct": "Manchester City"
    },
    {
        "question": "Which club plays at Camp Nou?",
        "answers": [
            "Barcelona",
            "Real Madrid",
            "Atlético Madrid",
            "Valencia"
        ],
        "correct": "Barcelona"
    },
    {
        "question": "Which club plays at the Santiago Bernabéu?",
        "answers": [
            "Real Madrid",
            "Barcelona",
            "Sevilla",
            "Athletic Club"
        ],
        "correct": "Real Madrid"
    },
    {
        "question": "Which club is nicknamed 'Los Blancos'?",
        "answers": [
            "Real Madrid",
            "Barcelona",
            "Atlético Madrid",
            "Valencia"
        ],
        "correct": "Real Madrid"
    },
    {
        "question": "Which club is nicknamed 'Blaugrana'?",
        "answers": [
            "Barcelona",
            "Real Madrid",
            "Sevilla",
            "Villarreal"
        ],
        "correct": "Barcelona"
    },
    {
        "question": "Which Italian club plays at San Siro?",
        "answers": [
            "AC Milan and Inter Milan",
            "Juventus and Torino",
            "Roma and Lazio",
            "Napoli and Salernitana"
        ],
        "correct": "AC Milan and Inter Milan"
    },
    {
        "question": "Which club plays at the Allianz Stadium in Turin?",
        "answers": [
            "Juventus",
            "Torino",
            "Inter Milan",
            "AC Milan"
        ],
        "correct": "Juventus"
    },
    {
        "question": "Which club is known as 'I Bianconeri'?",
        "answers": [
            "Juventus",
            "AC Milan",
            "Inter Milan",
            "Napoli"
        ],
        "correct": "Juventus"
    },
    {
        "question": "Which German club plays at Signal Iduna Park?",
        "answers": [
            "Borussia Dortmund",
            "Bayern Munich",
            "RB Leipzig",
            "Schalke 04"
        ],
        "correct": "Borussia Dortmund"
    },
    {
        "question": "Which German club is nicknamed 'Die Roten'?",
        "answers": [
            "Bayern Munich",
            "Borussia Dortmund",
            "Bayer Leverkusen",
            "Werder Bremen"
        ],
        "correct": "Bayern Munich"
    },
    {
        "question": "Which French club plays at Parc des Princes?",
        "answers": [
            "Paris Saint-Germain",
            "Marseille",
            "Lyon",
            "Monaco"
        ],
        "correct": "Paris Saint-Germain"
    },
    {
        "question": "Which club is nicknamed 'Les Parisiens'?",
        "answers": [
            "Paris Saint-Germain",
            "Marseille",
            "Lyon",
            "Monaco"
        ],
        "correct": "Paris Saint-Germain"
    },
    {
        "question": "Which club won the 1995 UEFA Champions League final?",
        "answers": [
            "Ajax",
            "AC Milan",
            "Juventus",
            "Barcelona"
        ],
        "correct": "Ajax"
    },
    {
        "question": "Which club won the 1983 European Cup?",
        "answers": [
            "Hamburg",
            "Juventus",
            "Liverpool",
            "Roma"
        ],
        "correct": "Hamburg"
    },
    {
        "question": "Which club won the 1984 European Cup?",
        "answers": [
            "Liverpool",
            "Roma",
            "Juventus",
            "Bayern Munich"
        ],
        "correct": "Liverpool"
    },
    {
        "question": "Which club won the 1985 European Cup?",
        "answers": [
            "Juventus",
            "Liverpool",
            "Everton",
            "Barcelona"
        ],
        "correct": "Juventus"
    },
    {
        "question": "Which country won UEFA Euro 2004?",
        "answers": [
            "Greece",
            "Portugal",
            "Spain",
            "France"
        ],
        "correct": "Greece"
    },
    {
        "question": "Which country won UEFA Euro 2008?",
        "answers": [
            "Spain",
            "Germany",
            "Italy",
            "Portugal"
        ],
        "correct": "Spain"
    },
    {
        "question": "Which country won UEFA Euro 2012?",
        "answers": [
            "Spain",
            "Italy",
            "Germany",
            "Portugal"
        ],
        "correct": "Spain"
    },
    {
        "question": "Which country won UEFA Euro 2016?",
        "answers": [
            "Portugal",
            "France",
            "Germany",
            "Spain"
        ],
        "correct": "Portugal"
    },
    {
        "question": "Which country won UEFA Euro 2020?",
        "answers": [
            "Italy",
            "England",
            "France",
            "Belgium"
        ],
        "correct": "Italy"
    },
    {
        "question": "Which country won UEFA Euro 2024?",
        "answers": [
            "Spain",
            "England",
            "Germany",
            "France"
        ],
        "correct": "Spain"
    },
    {
        "question": "Which country won UEFA Euro 2000?",
        "answers": [
            "France",
            "Italy",
            "Netherlands",
            "Portugal"
        ],
        "correct": "France"
    },
    {
        "question": "Which country won UEFA Euro 1996?",
        "answers": [
            "Germany",
            "England",
            "France",
            "Czech Republic"
        ],
        "correct": "Germany"
    },
    {
        "question": "Which country won UEFA Euro 1992?",
        "answers": [
            "Denmark",
            "Germany",
            "Sweden",
            "Netherlands"
        ],
        "correct": "Denmark"
    },
    {
        "question": "Which country won UEFA Euro 1988?",
        "answers": [
            "Netherlands",
            "West Germany",
            "Italy",
            "France"
        ],
        "correct": "Netherlands"
    },
    {
        "question": "Which country won UEFA Euro 1984?",
        "answers": [
            "France",
            "Spain",
            "Germany",
            "Belgium"
        ],
        "correct": "France"
    },
    {
        "question": "Which country won UEFA Euro 1980?",
        "answers": [
            "West Germany",
            "Belgium",
            "Italy",
            "Netherlands"
        ],
        "correct": "West Germany"
    },
    {
        "question": "Which country won UEFA Euro 1976?",
        "answers": [
            "Czechoslovakia",
            "West Germany",
            "Netherlands",
            "France"
        ],
        "correct": "Czechoslovakia"
    },
    {
        "question": "Which country won UEFA Euro 1972?",
        "answers": [
            "West Germany",
            "Soviet Union",
            "Belgium",
            "Italy"
        ],
        "correct": "West Germany"
    },
    {
        "question": "Which country won UEFA Euro 1968?",
        "answers": [
            "Italy",
            "Yugoslavia",
            "Soviet Union",
            "England"
        ],
        "correct": "Italy"
    },
    {
        "question": "Which country won UEFA Euro 1964?",
        "answers": [
            "Spain",
            "Soviet Union",
            "Hungary",
            "France"
        ],
        "correct": "Spain"
    },
    {
        "question": "Which country won the inaugural European Championship in 1960?",
        "answers": [
            "Soviet Union",
            "Yugoslavia",
            "Spain",
            "France"
        ],
        "correct": "Soviet Union"
    },
    {
        "question": "Which country hosted and won UEFA Euro 1984?",
        "answers": [
            "France",
            "Spain",
            "Germany",
            "Italy"
        ],
        "correct": "France"
    },
    {
        "question": "Which national team is nicknamed 'Azzurri'?",
        "answers": [
            "Italy",
            "France",
            "Spain",
            "Croatia"
        ],
        "correct": "Italy"
    },
    {
        "question": "Which national team is nicknamed 'La Roja'?",
        "answers": [
            "Spain",
            "Portugal",
            "Chile",
            "Mexico"
        ],
        "correct": "Spain"
    },
    {
        "question": "Which country does Cristiano Ronaldo represent?",
        "answers": [
            "Portugal",
            "Spain",
            "Brazil",
            "Argentina"
        ],
        "correct": "Portugal"
    },
    {
        "question": "Which country does Lionel Messi represent?",
        "answers": [
            "Argentina",
            "Brazil",
            "Uruguay",
            "Spain"
        ],
        "correct": "Argentina"
    },
    {
        "question": "Which country does Kylian Mbappé represent?",
        "answers": [
            "France",
            "Belgium",
            "Cameroon",
            "Spain"
        ],
        "correct": "France"
    },
    {
        "question": "Which country does Erling Haaland represent?",
        "answers": [
            "Norway",
            "Denmark",
            "Sweden",
            "Finland"
        ],
        "correct": "Norway"
    },
    {
        "question": "Which country does Vinícius Júnior represent?",
        "answers": [
            "Brazil",
            "Portugal",
            "Spain",
            "Colombia"
        ],
        "correct": "Brazil"
    },
    {
        "question": "Which country does Jude Bellingham represent?",
        "answers": [
            "England",
            "Scotland",
            "Wales",
            "Ireland"
        ],
        "correct": "England"
    },
    {
        "question": "Which country does Lamine Yamal represent?",
        "answers": [
            "Spain",
            "Morocco",
            "France",
            "Brazil"
        ],
        "correct": "Spain"
    },
    {
        "question": "Which country does Mohamed Salah represent?",
        "answers": [
            "Egypt",
            "Morocco",
            "Algeria",
            "Tunisia"
        ],
        "correct": "Egypt"
    },
    {
        "question": "Which country does Kevin De Bruyne represent?",
        "answers": [
            "Belgium",
            "Netherlands",
            "Germany",
            "France"
        ],
        "correct": "Belgium"
    },
    {
        "question": "Which country does Robert Lewandowski represent?",
        "answers": [
            "Poland",
            "Germany",
            "Czech Republic",
            "Ukraine"
        ],
        "correct": "Poland"
    },
    {
        "question": "Which country does Virgil van Dijk represent?",
        "answers": [
            "Netherlands",
            "Belgium",
            "Denmark",
            "Suriname"
        ],
        "correct": "Netherlands"
    },
    {
        "question": "Which country does Achraf Hakimi represent?",
        "answers": [
            "Morocco",
            "Algeria",
            "Tunisia",
            "Egypt"
        ],
        "correct": "Morocco"
    },
    {
        "question": "Which country does Bukayo Saka represent?",
        "answers": [
            "England",
            "Nigeria",
            "Ghana",
            "Scotland"
        ],
        "correct": "England"
    },
    {
        "question": "Which country does Rodri represent?",
        "answers": [
            "Spain",
            "Portugal",
            "Mexico",
            "Argentina"
        ],
        "correct": "Spain"
    },
    {
        "question": "Which country does Thibaut Courtois represent?",
        "answers": [
            "Belgium",
            "France",
            "Netherlands",
            "Luxembourg"
        ],
        "correct": "Belgium"
    },
    {
        "question": "Which country does Alisson Becker represent?",
        "answers": [
            "Brazil",
            "Argentina",
            "Portugal",
            "Chile"
        ],
        "correct": "Brazil"
    },
    {
        "question": "Which position is Cristiano Ronaldo most associated with?",
        "answers": [
            "Forward",
            "Goalkeeper",
            "Defender",
            "Central midfielder"
        ],
        "correct": "Forward"
    },
    {
        "question": "Which position is Thibaut Courtois?",
        "answers": [
            "Goalkeeper",
            "Striker",
            "Winger",
            "Defender"
        ],
        "correct": "Goalkeeper"
    },
    {
        "question": "Which position is Virgil van Dijk?",
        "answers": [
            "Centre-back",
            "Goalkeeper",
            "Winger",
            "Striker"
        ],
        "correct": "Centre-back"
    },
    {
        "question": "Which position is Mohamed Salah most associated with?",
        "answers": [
            "Winger/forward",
            "Goalkeeper",
            "Centre-back",
            "Defensive midfielder"
        ],
        "correct": "Winger/forward"
    },
    {
        "question": "Which club did Cristiano Ronaldo play for before Real Madrid in 2009?",
        "answers": [
            "Manchester United",
            "Arsenal",
            "Chelsea",
            "Liverpool"
        ],
        "correct": "Manchester United"
    },
    {
        "question": "Which club did Lionel Messi spend the majority of his senior career with?",
        "answers": [
            "Barcelona",
            "Real Madrid",
            "Atlético Madrid",
            "Sevilla"
        ],
        "correct": "Barcelona"
    },
    {
        "question": "Which club did Neymar join from Santos in 2013?",
        "answers": [
            "Barcelona",
            "Real Madrid",
            "Paris Saint-Germain",
            "Chelsea"
        ],
        "correct": "Barcelona"
    },
    {
        "question": "Which club did Kylian Mbappé join from Monaco in 2017?",
        "answers": [
            "Paris Saint-Germain",
            "Real Madrid",
            "Manchester City",
            "Lyon"
        ],
        "correct": "Paris Saint-Germain"
    },
    {
        "question": "Which club did Erling Haaland join from Borussia Dortmund in 2022?",
        "answers": [
            "Manchester City",
            "Chelsea",
            "Liverpool",
            "Arsenal"
        ],
        "correct": "Manchester City"
    },
    {
        "question": "Which club did Jude Bellingham join from Borussia Dortmund in 2023?",
        "answers": [
            "Real Madrid",
            "Chelsea",
            "Bayern Munich",
            "Manchester City"
        ],
        "correct": "Real Madrid"
    },
    {
        "question": "Which club did Vinícius Júnior join in Europe?",
        "answers": [
            "Real Madrid",
            "Barcelona",
            "Sevilla",
            "Valencia"
        ],
        "correct": "Real Madrid"
    },
    {
        "question": "Which club did Robert Lewandowski join from Bayern Munich in 2022?",
        "answers": [
            "Barcelona",
            "Real Madrid",
            "Inter Milan",
            "Paris Saint-Germain"
        ],
        "correct": "Barcelona"
    },
    {
        "question": "Which club did Mohamed Salah join in 2017?",
        "answers": [
            "Liverpool",
            "Chelsea",
            "Manchester United",
            "Arsenal"
        ],
        "correct": "Liverpool"
    },
    {
        "question": "Which club did Kevin De Bruyne join in 2015?",
        "answers": [
            "Manchester City",
            "Chelsea",
            "Liverpool",
            "Tottenham Hotspur"
        ],
        "correct": "Manchester City"
    },
    {
        "question": "Which club did Rodri join in 2019?",
        "answers": [
            "Manchester City",
            "Atlético Madrid",
            "Barcelona",
            "Real Madrid"
        ],
        "correct": "Manchester City"
    },
    {
        "question": "Which club did Achraf Hakimi join in 2021?",
        "answers": [
            "Paris Saint-Germain",
            "Chelsea",
            "Inter Milan",
            "Real Madrid"
        ],
        "correct": "Paris Saint-Germain"
    },
    {
        "question": "Which club did Thibaut Courtois join in 2018?",
        "answers": [
            "Real Madrid",
            "Chelsea",
            "Atlético Madrid",
            "Barcelona"
        ],
        "correct": "Real Madrid"
    },
    {
        "question": "Which club did Alisson Becker join in 2018?",
        "answers": [
            "Liverpool",
            "Chelsea",
            "Manchester City",
            "Arsenal"
        ],
        "correct": "Liverpool"
    },
    {
        "question": "Which club did Virgil van Dijk join in January 2018?",
        "answers": [
            "Liverpool",
            "Southampton",
            "Chelsea",
            "Manchester City"
        ],
        "correct": "Liverpool"
    },
    {
        "question": "Which club did Harry Kane leave in 2023?",
        "answers": [
            "Tottenham Hotspur",
            "Leicester City",
            "Chelsea",
            "Arsenal"
        ],
        "correct": "Tottenham Hotspur"
    },
    {
        "question": "Which club did Karim Benzema leave in 2023?",
        "answers": [
            "Real Madrid",
            "Lyon",
            "Juventus",
            "Inter Milan"
        ],
        "correct": "Real Madrid"
    },
    {
        "question": "Which club did Sadio Mané join in 2023?",
        "answers": [
            "Al Nassr",
            "Liverpool",
            "Bayern Munich",
            "Chelsea"
        ],
        "correct": "Al Nassr"
    },
    {
        "question": "Which club did Gareth Bale join from Tottenham Hotspur in 2013?",
        "answers": [
            "Real Madrid",
            "Barcelona",
            "Manchester United",
            "Paris Saint-Germain"
        ],
        "correct": "Real Madrid"
    },
    {
        "question": "Which club did Luis Suárez join from Liverpool in 2014?",
        "answers": [
            "Barcelona",
            "Atlético Madrid",
            "Juventus",
            "Inter Milan"
        ],
        "correct": "Barcelona"
    },
    {
        "question": "How many players does one team normally have on the field?",
        "answers": [
            "11",
            "10",
            "12",
            "9"
        ],
        "correct": "11"
    },
    {
        "question": "How long is a standard football match, excluding added time?",
        "answers": [
            "90 minutes",
            "80 minutes",
            "100 minutes",
            "120 minutes"
        ],
        "correct": "90 minutes"
    },
    {
        "question": "How many halves are in a standard football match?",
        "answers": [
            "2",
            "3",
            "4",
            "1"
        ],
        "correct": "2"
    },
    {
        "question": "How long is each regulation half?",
        "answers": [
            "45 minutes",
            "40 minutes",
            "50 minutes",
            "35 minutes"
        ],
        "correct": "45 minutes"
    },
    {
        "question": "How many points does a league win normally give?",
        "answers": [
            "3",
            "2",
            "1",
            "4"
        ],
        "correct": "3"
    },
    {
        "question": "How many points does a league draw normally give each team?",
        "answers": [
            "1",
            "3",
            "2",
            "0"
        ],
        "correct": "1"
    },
    {
        "question": "What card normally means a player is sent off?",
        "answers": [
            "Red",
            "Yellow",
            "Blue",
            "Green"
        ],
        "correct": "Red"
    },
    {
        "question": "What card is normally a caution?",
        "answers": [
            "Yellow",
            "Red",
            "Blue",
            "White"
        ],
        "correct": "Yellow"
    },
    {
        "question": "Which position is primarily responsible for stopping shots?",
        "answers": [
            "Goalkeeper",
            "Striker",
            "Winger",
            "Full-back"
        ],
        "correct": "Goalkeeper"
    },
    {
        "question": "Which position usually plays centrally in defense?",
        "answers": [
            "Centre-back",
            "Winger",
            "Striker",
            "Goalkeeper"
        ],
        "correct": "Centre-back"
    },
    {
        "question": "Which position usually plays wide in defense?",
        "answers": [
            "Full-back",
            "Striker",
            "Centre-back",
            "Goalkeeper"
        ],
        "correct": "Full-back"
    },
    {
        "question": "Which position is usually the main central attacking role?",
        "answers": [
            "Striker",
            "Goalkeeper",
            "Centre-back",
            "Full-back"
        ],
        "correct": "Striker"
    },
    {
        "question": "What is a hat-trick?",
        "answers": [
            "Three goals by one player",
            "Three assists by one player",
            "Three yellow cards",
            "Three saves"
        ],
        "correct": "Three goals by one player"
    },
    {
        "question": "What is a clean sheet?",
        "answers": [
            "Conceding no goals",
            "Scoring no goals",
            "Winning by five",
            "Keeping possession above 60%"
        ],
        "correct": "Conceding no goals"
    },
    {
        "question": "What does VAR stand for?",
        "answers": [
            "Video Assistant Referee",
            "Virtual Attack Review",
            "Video Analysis Rule",
            "Verified Assistant Replay"
        ],
        "correct": "Video Assistant Referee"
    },
    {
        "question": "How many penalty kicks are usually taken per team in the first round of a shootout?",
        "answers": [
            "5",
            "3",
            "4",
            "6"
        ],
        "correct": "5"
    },
    {
        "question": "Where is a penalty kick taken from?",
        "answers": [
            "Penalty spot",
            "Centre circle",
            "Six-yard line",
            "Corner arc"
        ],
        "correct": "Penalty spot"
    },
    {
        "question": "What restarts play after the ball crosses the sideline?",
        "answers": [
            "Throw-in",
            "Corner kick",
            "Goal kick",
            "Drop ball"
        ],
        "correct": "Throw-in"
    },
    {
        "question": "What restarts play after an attacking player last touches the ball over the goal line?",
        "answers": [
            "Goal kick",
            "Corner kick",
            "Throw-in",
            "Free kick"
        ],
        "correct": "Goal kick"
    },
    {
        "question": "What restarts play after a defending player last touches the ball over the goal line?",
        "answers": [
            "Corner kick",
            "Goal kick",
            "Throw-in",
            "Drop ball"
        ],
        "correct": "Corner kick"
    },
    {
        "question": "Which country is famous for the yellow-and-blue national colors in football?",
        "answers": [
            "Brazil",
            "Argentina",
            "Uruguay",
            "Colombia"
        ],
        "correct": "Brazil"
    },
    {
        "question": "Which club is famous for the 'You'll Never Walk Alone' anthem?",
        "answers": [
            "Liverpool",
            "Arsenal",
            "Chelsea",
            "Everton"
        ],
        "correct": "Liverpool"
    },
    {
        "question": "Which club is famous for the 'Mia San Mia' motto?",
        "answers": [
            "Bayern Munich",
            "Borussia Dortmund",
            "Bayer Leverkusen",
            "Schalke 04"
        ],
        "correct": "Bayern Munich"
    },
    {
        "question": "Which club is commonly called 'Los Colchoneros'?",
        "answers": [
            "Atlético Madrid",
            "Real Madrid",
            "Barcelona",
            "Sevilla"
        ],
        "correct": "Atlético Madrid"
    },
    {
        "question": "Which club is commonly called 'The Old Lady'?",
        "answers": [
            "Juventus",
            "Inter Milan",
            "AC Milan",
            "Roma"
        ],
        "correct": "Juventus"
    },
    {
        "question": "Which club is commonly called 'The Reds' of Merseyside?",
        "answers": [
            "Liverpool",
            "Everton",
            "Burnley",
            "Leicester City"
        ],
        "correct": "Liverpool"
    },
    {
        "question": "Which club is commonly called 'The Lilywhites'?",
        "answers": [
            "Tottenham Hotspur",
            "Leeds United",
            "Fulham",
            "Southampton"
        ],
        "correct": "Tottenham Hotspur"
    },
    {
        "question": "Which club is commonly called 'The Foxes'?",
        "answers": [
            "Leicester City",
            "Wolves",
            "Aston Villa",
            "Everton"
        ],
        "correct": "Leicester City"
    },
    {
        "question": "Which club is commonly called 'The Citizens'?",
        "answers": [
            "Manchester City",
            "Manchester United",
            "Chelsea",
            "Leicester City"
        ],
        "correct": "Manchester City"
    },
    {
        "question": "Which club is commonly called 'The Hammers'?",
        "answers": [
            "West Ham United",
            "Newcastle United",
            "Arsenal",
            "Fulham"
        ],
        "correct": "West Ham United"
    },
    {
        "question": "Which city is home to Real Madrid?",
        "answers": [
            "Madrid",
            "Barcelona",
            "Seville",
            "Valencia"
        ],
        "correct": "Madrid"
    },
    {
        "question": "Which city is home to Liverpool FC?",
        "answers": [
            "Liverpool",
            "Manchester",
            "Leeds",
            "Birmingham"
        ],
        "correct": "Liverpool"
    },
    {
        "question": "Which city is home to Bayern Munich?",
        "answers": [
            "Munich",
            "Berlin",
            "Hamburg",
            "Frankfurt"
        ],
        "correct": "Munich"
    },
    {
        "question": "Which city is home to Paris Saint-Germain?",
        "answers": [
            "Paris",
            "Lyon",
            "Marseille",
            "Nice"
        ],
        "correct": "Paris"
    },
    {
        "question": "Which city is home to Juventus?",
        "answers": [
            "Turin",
            "Milan",
            "Rome",
            "Naples"
        ],
        "correct": "Turin"
    },
    {
        "question": "In which country is Real Madrid based?",
        "answers": [
            "Spain",
            "England",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Barcelona based?",
        "answers": [
            "Spain",
            "England",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Atlético Madrid based?",
        "answers": [
            "Spain",
            "England",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Liverpool based?",
        "answers": [
            "England",
            "Spain",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Manchester United based?",
        "answers": [
            "England",
            "Spain",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Manchester City based?",
        "answers": [
            "England",
            "Spain",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Arsenal based?",
        "answers": [
            "England",
            "Spain",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Chelsea based?",
        "answers": [
            "England",
            "Spain",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Tottenham Hotspur based?",
        "answers": [
            "England",
            "Spain",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Bayern Munich based?",
        "answers": [
            "Germany",
            "Spain",
            "England",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Borussia Dortmund based?",
        "answers": [
            "Germany",
            "Spain",
            "England",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Bayer Leverkusen based?",
        "answers": [
            "Germany",
            "Spain",
            "England",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Juventus based?",
        "answers": [
            "Italy",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "In which country is AC Milan based?",
        "answers": [
            "Italy",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Inter Milan based?",
        "answers": [
            "Italy",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Roma based?",
        "answers": [
            "Italy",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Paris Saint-Germain based?",
        "answers": [
            "France",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Marseille based?",
        "answers": [
            "France",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Lyon based?",
        "answers": [
            "France",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Monaco based?",
        "answers": [
            "France",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Ajax based?",
        "answers": [
            "Netherlands",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "In which country is PSV Eindhoven based?",
        "answers": [
            "Netherlands",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Porto based?",
        "answers": [
            "Portugal",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Benfica based?",
        "answers": [
            "Portugal",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Sporting CP based?",
        "answers": [
            "Portugal",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Galatasaray based?",
        "answers": [
            "Türkiye",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Fenerbahçe based?",
        "answers": [
            "Türkiye",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Celtic based?",
        "answers": [
            "Scotland",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Rangers based?",
        "answers": [
            "Scotland",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "In which country is River Plate based?",
        "answers": [
            "Argentina",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Boca Juniors based?",
        "answers": [
            "Argentina",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Flamengo based?",
        "answers": [
            "Brazil",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Santos based?",
        "answers": [
            "Brazil",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "In which country is Corinthians based?",
        "answers": [
            "Brazil",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "Which club is based at Wembley Stadium when England play international home matches?",
        "answers": [
            "England",
            "Chelsea",
            "Arsenal",
            "Tottenham Hotspur"
        ],
        "correct": "England"
    },
    {
        "question": "Which club was founded in 1902 and is one of the world's most famous clubs?",
        "answers": [
            "Real Madrid",
            "Barcelona",
            "Liverpool",
            "Bayern Munich"
        ],
        "correct": "Real Madrid"
    },
    {
        "question": "Which club is associated with the city of Naples?",
        "answers": [
            "Napoli",
            "Roma",
            "Lazio",
            "Fiorentina"
        ],
        "correct": "Napoli"
    },
    {
        "question": "Which club is associated with the city of Florence?",
        "answers": [
            "Fiorentina",
            "Napoli",
            "Roma",
            "Lazio"
        ],
        "correct": "Fiorentina"
    },
    {
        "question": "Which club is associated with the city of Rome and wears sky blue?",
        "answers": [
            "Lazio",
            "Roma",
            "Napoli",
            "Torino"
        ],
        "correct": "Lazio"
    },
    {
        "question": "Which club is associated with the city of Rome and wears maroon and gold?",
        "answers": [
            "Roma",
            "Lazio",
            "Napoli",
            "Fiorentina"
        ],
        "correct": "Roma"
    },
    {
        "question": "Which club is associated with Marseille?",
        "answers": [
            "Olympique de Marseille",
            "Lyon",
            "Monaco",
            "Nice"
        ],
        "correct": "Olympique de Marseille"
    },
    {
        "question": "Which club is associated with Rotterdam?",
        "answers": [
            "Feyenoord",
            "Ajax",
            "PSV",
            "AZ Alkmaar"
        ],
        "correct": "Feyenoord"
    },
    {
        "question": "Which club is associated with Eindhoven?",
        "answers": [
            "PSV Eindhoven",
            "Ajax",
            "Feyenoord",
            "Twente"
        ],
        "correct": "PSV Eindhoven"
    },
    {
        "question": "Which club is associated with Glasgow and green-and-white colors?",
        "answers": [
            "Celtic",
            "Rangers",
            "Hearts",
            "Aberdeen"
        ],
        "correct": "Celtic"
    },
    {
        "question": "Which club is associated with Glasgow and blue colors?",
        "answers": [
            "Rangers",
            "Celtic",
            "Hearts",
            "Hibernian"
        ],
        "correct": "Rangers"
    },
    {
        "question": "Which club is associated with Lisbon and red-and-white colors?",
        "answers": [
            "Benfica",
            "Sporting CP",
            "Porto",
            "Braga"
        ],
        "correct": "Benfica"
    },
    {
        "question": "Which club is associated with Lisbon and green-and-white colors?",
        "answers": [
            "Sporting CP",
            "Benfica",
            "Porto",
            "Braga"
        ],
        "correct": "Sporting CP"
    },
    {
        "question": "Which club is associated with Porto?",
        "answers": [
            "FC Porto",
            "Benfica",
            "Sporting CP",
            "Boavista"
        ],
        "correct": "FC Porto"
    },
    {
        "question": "Which Brazilian club is famous for producing Pelé?",
        "answers": [
            "Santos",
            "Flamengo",
            "Corinthians",
            "Palmeiras"
        ],
        "correct": "Santos"
    },
    {
        "question": "Which Argentine club is based in La Boca?",
        "answers": [
            "Boca Juniors",
            "River Plate",
            "Racing Club",
            "Independiente"
        ],
        "correct": "Boca Juniors"
    },
    {
        "question": "Which Argentine club is nicknamed 'Los Millonarios'?",
        "answers": [
            "River Plate",
            "Boca Juniors",
            "Racing Club",
            "San Lorenzo"
        ],
        "correct": "River Plate"
    },
    {
        "question": "Which Brazilian club is based in Rio de Janeiro and wears red-black?",
        "answers": [
            "Flamengo",
            "Fluminense",
            "Botafogo",
            "Vasco da Gama"
        ],
        "correct": "Flamengo"
    },
    {
        "question": "Which Brazilian club is based in São Paulo and is famous for black-white colors?",
        "answers": [
            "Corinthians",
            "Santos",
            "Palmeiras",
            "São Paulo FC"
        ],
        "correct": "Corinthians"
    },
    {
        "question": "Which club is known for the 'Rossoneri' nickname?",
        "answers": [
            "AC Milan",
            "Inter Milan",
            "Juventus",
            "Roma"
        ],
        "correct": "AC Milan"
    },
    {
        "question": "Which country is the club Real Madrid from?",
        "answers": [
            "Spain",
            "England",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Which nation is represented by club Real Madrid?",
        "answers": [
            "Spain",
            "England",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Real Madrid is a club from which country?",
        "answers": [
            "Spain",
            "England",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Which country is the club Barcelona from?",
        "answers": [
            "Spain",
            "England",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Which nation is represented by club Barcelona?",
        "answers": [
            "Spain",
            "England",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Barcelona is a club from which country?",
        "answers": [
            "Spain",
            "England",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Which country is the club Liverpool from?",
        "answers": [
            "England",
            "Spain",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Which nation is represented by club Liverpool?",
        "answers": [
            "England",
            "Spain",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Liverpool is a club from which country?",
        "answers": [
            "England",
            "Spain",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Which country is the club Manchester United from?",
        "answers": [
            "England",
            "Spain",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Which nation is represented by club Manchester United?",
        "answers": [
            "England",
            "Spain",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Manchester United is a club from which country?",
        "answers": [
            "England",
            "Spain",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Which country is the club Manchester City from?",
        "answers": [
            "England",
            "Spain",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Which nation is represented by club Manchester City?",
        "answers": [
            "England",
            "Spain",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Manchester City is a club from which country?",
        "answers": [
            "England",
            "Spain",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Which country is the club Arsenal from?",
        "answers": [
            "England",
            "Spain",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Which nation is represented by club Arsenal?",
        "answers": [
            "England",
            "Spain",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Arsenal is a club from which country?",
        "answers": [
            "England",
            "Spain",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Which country is the club Chelsea from?",
        "answers": [
            "England",
            "Spain",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Which nation is represented by club Chelsea?",
        "answers": [
            "England",
            "Spain",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Chelsea is a club from which country?",
        "answers": [
            "England",
            "Spain",
            "Germany",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Which country is the club Bayern Munich from?",
        "answers": [
            "Germany",
            "Spain",
            "England",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Which nation is represented by club Bayern Munich?",
        "answers": [
            "Germany",
            "Spain",
            "England",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Bayern Munich is a club from which country?",
        "answers": [
            "Germany",
            "Spain",
            "England",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Which country is the club Borussia Dortmund from?",
        "answers": [
            "Germany",
            "Spain",
            "England",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Which nation is represented by club Borussia Dortmund?",
        "answers": [
            "Germany",
            "Spain",
            "England",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Borussia Dortmund is a club from which country?",
        "answers": [
            "Germany",
            "Spain",
            "England",
            "Italy"
        ],
        "correct": 0
    },
    {
        "question": "Which country is the club Juventus from?",
        "answers": [
            "Italy",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "Which nation is represented by club Juventus?",
        "answers": [
            "Italy",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "Juventus is a club from which country?",
        "answers": [
            "Italy",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "Which country is the club AC Milan from?",
        "answers": [
            "Italy",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "Which nation is represented by club AC Milan?",
        "answers": [
            "Italy",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "AC Milan is a club from which country?",
        "answers": [
            "Italy",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    },
    {
        "question": "Which country is the club Inter Milan from?",
        "answers": [
            "Italy",
            "Spain",
            "England",
            "Germany"
        ],
        "correct": 0
    }
]

QUESTIONS_EN = QUESTIONS

# =========================================================
# FRENCH QUIZ BANK
# =========================================================
# Static French bank: no runtime translation service is used.
# IDs intentionally match QUESTIONS_EN.
QUESTIONS_FR = [{'question': 'Quel pays a remporté la Coupe du monde de la FIFA en 1930 ?',
  'answers': ['Argentine', 'Brésil', 'Uruguay', 'Allemagne'],
  'correct': 2},
 {'question': 'Quel pays a remporté la Coupe du monde de la FIFA en 1934 ?',
  'answers': ['Argentine', 'Brésil', 'Italie', 'Allemagne'],
  'correct': 2},
 {'question': 'Quel pays a remporté la Coupe du monde de la FIFA en 1938 ?',
  'answers': ['Italie', 'Allemagne', 'Argentine', 'Brésil'],
  'correct': 0},
 {'question': 'Quel pays a remporté la Coupe du monde de la FIFA en 1950 ?',
  'answers': ['Argentine', 'Allemagne', 'Uruguay', 'Brésil'],
  'correct': 2},
 {'question': 'Quel pays a remporté la Coupe du monde de la FIFA en 1954 ?',
  'answers': ['Allemagne', 'Brésil', 'Argentine', 'Allemagne de l’Ouest'],
  'correct': 3},
 {'question': 'Quel pays a remporté la Coupe du monde de la FIFA en 1958 ?',
  'answers': ['Allemagne', 'France', 'Brésil', 'Argentine'],
  'correct': 2},
 {'question': 'Quel pays a remporté la Coupe du monde de la FIFA en 1962 ?',
  'answers': ['France', 'Brésil', 'Allemagne', 'Argentine'],
  'correct': 1},
 {'question': 'Quel pays a remporté la Coupe du monde de la FIFA en 1966 ?',
  'answers': ['Angleterre', 'Brésil', 'Argentine', 'Allemagne'],
  'correct': 0},
 {'question': 'Quel pays a remporté la Coupe du monde de la FIFA en 1970 ?',
  'answers': ['Allemagne', 'Brésil', 'Argentine', 'France'],
  'correct': 1},
 {'question': 'Quel pays a remporté la Coupe du monde de la FIFA en 1974 ?',
  'answers': ['Brésil', 'Allemagne', 'Argentine', 'Allemagne de l’Ouest'],
  'correct': 3},
 {'question': 'Quel pays a remporté la Coupe du monde de la FIFA en 1978 ?',
  'answers': ['Allemagne', 'Brésil', 'France', 'Argentine'],
  'correct': 3},
 {'question': 'Quel pays a remporté la Coupe du monde de la FIFA en 1982 ?',
  'answers': ['Argentine', 'Brésil', 'Italie', 'Allemagne'],
  'correct': 2},
 {'question': 'Quel pays a remporté la Coupe du monde de la FIFA en 1986 ?',
  'answers': ['Argentine', 'Brésil', 'France', 'Allemagne'],
  'correct': 0},
 {'question': 'Quel pays a remporté la Coupe du monde de la FIFA en 1990 ?',
  'answers': ['Allemagne de l’Ouest', 'Argentine', 'Allemagne', 'Brésil'],
  'correct': 0},
 {'question': 'Quel pays a remporté la Coupe du monde de la FIFA en 1994 ?',
  'answers': ['Brésil', 'France', 'Argentine', 'Allemagne'],
  'correct': 0},
 {'question': 'Quel pays a remporté la Coupe du monde de la FIFA en 1998 ?',
  'answers': ['Brésil', 'France', 'Argentine', 'Allemagne'],
  'correct': 1},
 {'question': 'Quel pays a remporté la Coupe du monde de la FIFA en 2002 ?',
  'answers': ['Brésil', 'France', 'Argentine', 'Allemagne'],
  'correct': 0},
 {'question': 'Quel pays a remporté la Coupe du monde de la FIFA en 2006 ?',
  'answers': ['Italie', 'Brésil', 'Argentine', 'Allemagne'],
  'correct': 0},
 {'question': 'Quel pays a remporté la Coupe du monde de la FIFA en 2010 ?',
  'answers': ['Allemagne', 'Argentine', 'Brésil', 'Espagne'],
  'correct': 3},
 {'question': 'Quel pays a remporté la Coupe du monde de la FIFA en 2014 ?',
  'answers': ['Argentine', 'Allemagne', 'Brésil', 'France'],
  'correct': 1},
 {'question': 'Quel pays a remporté la Coupe du monde de la FIFA en 2018 ?',
  'answers': ['Argentine', 'Brésil', 'Allemagne', 'France'],
  'correct': 3},
 {'question': 'Quel pays a remporté la Coupe du monde de la FIFA en 2022 ?',
  'answers': ['Argentine', 'Allemagne', 'Brésil', 'France'],
  'correct': 0},
 {'question': 'Quel pays a accueilli la Coupe du monde de la FIFA 2014 ?',
  'answers': ['Brésil', 'Russia', 'Allemagne', 'Afrique du Sud'],
  'correct': 'Brésil'},
 {'question': 'Quel pays a accueilli la Coupe du monde de la FIFA 2010 ?',
  'answers': ['Afrique du Sud', 'Brésil', 'Allemagne', 'France'],
  'correct': 'Afrique du Sud'},
 {'question': 'Quel pays a accueilli la Coupe du monde de la FIFA 2006 ?',
  'answers': ['Allemagne', 'Italie', 'France', 'Espagne'],
  'correct': 'Allemagne'},
 {'question': 'Quels pays ont co-organisé la Coupe du monde de la FIFA 2002 ?',
  'answers': ['Japon et Corée du Sud',
              'China and Japan',
              'Japan and China',
              'South Korea and China'],
  'correct': 'Japon et Corée du Sud'},
 {'question': 'Quel joueur a inscrit le célèbre but de la « Main de Dieu » lors de la Coupe du '
              'monde 1986 ?',
  'answers': ['Diego Maradona', 'Pelé', 'Zinedine Zidane', 'Johan Cruyff'],
  'correct': 'Diego Maradona'},
 {'question': 'Quelle équipe a perdu la finale de la Coupe du monde 2010 contre Spain ?',
  'answers': ['Pays-Bas', 'Allemagne', 'Italie', 'Brésil'],
  'correct': 'Pays-Bas'},
 {'question': 'Quelle équipe a perdu la finale de la Coupe du monde 2014 contre Germany ?',
  'answers': ['Argentine', 'Brésil', 'Pays-Bas', 'France'],
  'correct': 'Argentine'},
 {'question': 'Quelle équipe a perdu la finale de la Coupe du monde 2018 contre France ?',
  'answers': ['Croatie', 'Belgique', 'Argentine', 'Angleterre'],
  'correct': 'Croatie'},
 {'question': 'Quelle équipe a perdu la finale de la Coupe du monde 2022 contre Argentina ?',
  'answers': ['France', 'Croatie', 'Brésil', 'Angleterre'],
  'correct': 'France'},
 {'question': 'Quel pays a remporté la première Coupe du monde en 1930 ?',
  'answers': ['Uruguay', 'Argentine', 'Brésil', 'Italie'],
  'correct': 'Uruguay'},
 {'question': 'Qui a remporté le Ballon d’Or 2008 ?',
  'answers': ['Cristiano Ronaldo', 'Lionel Messi', 'Kaká', 'Xavi'],
  'correct': 'Cristiano Ronaldo'},
 {'question': 'Qui a remporté le Ballon d’Or 2007 ?',
  'answers': ['Kaká', 'Cristiano Ronaldo', 'Lionel Messi', 'Ronaldinho'],
  'correct': 'Kaká'},
 {'question': 'Qui a remporté le Ballon d’Or 2006 ?',
  'answers': ['Fabio Cannavaro', 'Ronaldinho', 'Zinedine Zidane', 'Andriy Shevchenko'],
  'correct': 'Fabio Cannavaro'},
 {'question': 'Qui a remporté le Ballon d’Or 2005 ?',
  'answers': ['Ronaldinho', 'Lionel Messi', 'Kaká', 'Frank Lampard'],
  'correct': 'Ronaldinho'},
 {'question': 'Qui a remporté le Ballon d’Or 2004 ?',
  'answers': ['Andriy Shevchenko', 'Pavel Nedvěd', 'Ronaldinho', 'Ronaldo Nazário'],
  'correct': 'Andriy Shevchenko'},
 {'question': 'Qui a remporté le Ballon d’Or 2003 ?',
  'answers': ['Pavel Nedvěd', 'Zinedine Zidane', 'Ronaldo Nazário', 'Thierry Henry'],
  'correct': 'Pavel Nedvěd'},
 {'question': 'Qui a remporté le Ballon d’Or 2002 ?',
  'answers': ['Ronaldo Nazário', 'Michael Ballack', 'Roberto Carlos', 'Raúl'],
  'correct': 'Ronaldo Nazário'},
 {'question': 'Qui a remporté le Ballon d’Or 2001 ?',
  'answers': ['Michael Owen', 'David Beckham', 'Luis Figo', 'Raúl'],
  'correct': 'Michael Owen'},
 {'question': 'Qui a remporté le Ballon d’Or 2000 ?',
  'answers': ['Luís Figo', 'Zinedine Zidane', 'Rivaldo', 'Franz Beckenbauer'],
  'correct': 'Luís Figo'},
 {'question': 'Qui a remporté le Ballon d’Or 1999 ?',
  'answers': ['Rivaldo', 'David Beckham', 'Gabriel Batistuta', 'Ronaldo Nazário'],
  'correct': 'Rivaldo'},
 {'question': 'Qui a remporté le Ballon d’Or 1998 ?',
  'answers': ['Zinedine Zidane', 'Ronaldo Nazário', 'Davor Šuker', 'Luís Figo'],
  'correct': 'Zinedine Zidane'},
 {'question': 'Qui a remporté le Ballon d’Or 1997 ?',
  'answers': ['Ronaldo Nazário', 'Roberto Carlos', 'Dennis Bergkamp', 'Zinedine Zidane'],
  'correct': 'Ronaldo Nazário'},
 {'question': 'Qui a remporté le Ballon d’Or 1996 ?',
  'answers': ['Matthias Sammer', 'Ronaldo Nazário', 'Alan Shearer', 'George Weah'],
  'correct': 'Matthias Sammer'},
 {'question': 'Qui a remporté le Ballon d’Or 1995 ?',
  'answers': ['George Weah', 'Jari Litmanen', 'Milan Baroš', 'Romário'],
  'correct': 'George Weah'},
 {'question': 'Qui a remporté le Ballon d’Or 1994 ?',
  'answers': ['Hristo Stoichkov', 'Roberto Baggio', 'Paolo Maldini', 'Romário'],
  'correct': 'Hristo Stoichkov'},
 {'question': 'Qui a remporté le Ballon d’Or 1993 ?',
  'answers': ['Roberto Baggio', 'Dennis Bergkamp', 'Eric Cantona', 'Jean-Pierre Papin'],
  'correct': 'Roberto Baggio'},
 {'question': 'Qui a remporté le Ballon d’Or 1992 ?',
  'answers': ['Marco van Basten', 'Dennis Bergkamp', 'Gary Lineker', 'Hristo Stoichkov'],
  'correct': 'Marco van Basten'},
 {'question': 'Qui a remporté le Ballon d’Or 1991 ?',
  'answers': ['Jean-Pierre Papin', 'Lothar Matthäus', 'Marco van Basten', 'Michael Laudrup'],
  'correct': 'Jean-Pierre Papin'},
 {'question': 'Qui a remporté le Ballon d’Or 1990 ?',
  'answers': ['Lothar Matthäus', 'Salvatore Schillaci', 'Diego Maradona', 'Andreas Brehme'],
  'correct': 'Lothar Matthäus'},
 {'question': 'Qui a remporté le Ballon d’Or 1989 ?',
  'answers': ['Marco van Basten', 'Ruud Gullit', 'Franco Baresi', 'Roberto Baggio'],
  'correct': 'Marco van Basten'},
 {'question': 'Quel club a remporté le plus de titres en Coupe d’Europe / Ligue des champions de '
              'l’UEFA ?',
  'answers': ['Real Madrid', 'AC Milan', 'Bayern Munich', 'Liverpool'],
  'correct': 'Real Madrid'},
 {'question': 'Quel club a remporté la Ligue des champions de l’UEFA 1993 ?',
  'answers': ['Marseille', 'AC Milan', 'Barcelona', 'Juventus'],
  'correct': 'Marseille'},
 {'question': 'Quel club a remporté la Ligue des champions de l’UEFA 2005 à Istanbul ?',
  'answers': ['Liverpool', 'AC Milan', 'Chelsea', 'Barcelona'],
  'correct': 'Liverpool'},
 {'question': 'Quel club a remporté la Ligue des champions de l’UEFA 2012 ?',
  'answers': ['Chelsea', 'Bayern Munich', 'Real Madrid', 'Barcelona'],
  'correct': 'Chelsea'},
 {'question': 'Quel club a remporté la Ligue des champions de l’UEFA 2013 ?',
  'answers': ['Bayern Munich', 'Borussia Dortmund', 'Real Madrid', 'Manchester United'],
  'correct': 'Bayern Munich'},
 {'question': 'Quel club a remporté la Ligue des champions de l’UEFA 2014 ?',
  'answers': ['Real Madrid', 'Atlético Madrid', 'Bayern Munich', 'Chelsea'],
  'correct': 'Real Madrid'},
 {'question': 'Quel club a remporté la Ligue des champions de l’UEFA 2018 ?',
  'answers': ['Real Madrid', 'Liverpool', 'Bayern Munich', 'Barcelona'],
  'correct': 'Real Madrid'},
 {'question': 'Quel club a remporté la Ligue des champions de l’UEFA 2019 ?',
  'answers': ['Liverpool', 'Tottenham Hotspur', 'Ajax', 'Barcelona'],
  'correct': 'Liverpool'},
 {'question': 'Quel club a remporté la Ligue des champions de l’UEFA 2020 ?',
  'answers': ['Bayern Munich', 'Paris Saint-Germain', 'Liverpool', 'Manchester City'],
  'correct': 'Bayern Munich'},
 {'question': 'Quel club a remporté la Ligue des champions de l’UEFA 2021 ?',
  'answers': ['Chelsea', 'Manchester City', 'Bayern Munich', 'Paris Saint-Germain'],
  'correct': 'Chelsea'},
 {'question': 'Quel club a remporté la Ligue des champions de l’UEFA 2022 ?',
  'answers': ['Real Madrid', 'Liverpool', 'Manchester City', 'Chelsea'],
  'correct': 'Real Madrid'},
 {'question': 'Quel club a remporté la Ligue des champions de l’UEFA 2023 ?',
  'answers': ['Manchester City', 'Inter Milan', 'Real Madrid', 'Bayern Munich'],
  'correct': 'Manchester City'},
 {'question': 'Quel club a remporté la Ligue des champions de l’UEFA 2008-09 ?',
  'answers': ['Barcelona', 'Manchester United', 'Chelsea', 'Arsenal'],
  'correct': 'Barcelona'},
 {'question': 'Quel club a remporté la Ligue des champions de l’UEFA 2006-07 ?',
  'answers': ['AC Milan', 'Liverpool', 'Manchester United', 'Barcelona'],
  'correct': 'AC Milan'},
 {'question': 'Quel club a remporté la Ligue des champions de l’UEFA 2004-05 ?',
  'answers': ['Liverpool', 'AC Milan', 'Chelsea', 'Juventus'],
  'correct': 'Liverpool'},
 {'question': 'Quel club a remporté la Ligue des champions de l’UEFA 2010-11 ?',
  'answers': ['Barcelona', 'Manchester United', 'Real Madrid', 'Inter Milan'],
  'correct': 'Barcelona'},
 {'question': 'Quel club a remporté la Ligue des champions de l’UEFA 2015 ?',
  'answers': ['Barcelona', 'Juventus', 'Real Madrid', 'Bayern Munich'],
  'correct': 'Barcelona'},
 {'question': 'Quel club a remporté la finale de la Ligue des champions 1999 ?',
  'answers': ['Manchester United', 'Bayern Munich', 'Real Madrid', 'Valencia'],
  'correct': 'Manchester United'},
 {'question': 'Quel club anglais a remporté 1977 European Cup ?',
  'answers': ['Liverpool', 'Nottingham Forest', 'Aston Villa', 'Manchester United'],
  'correct': 'Liverpool'},
 {'question': 'Quel club anglais a remporté 1979 European Cup ?',
  'answers': ['Nottingham Forest', 'Liverpool', 'Aston Villa', 'Manchester United'],
  'correct': 'Nottingham Forest'},
 {'question': 'Quel club anglais a remporté 1980 European Cup ?',
  'answers': ['Nottingham Forest', 'Liverpool', 'Chelsea', 'Manchester United'],
  'correct': 'Nottingham Forest'},
 {'question': 'Quel club italien a remporté 2010 Champions League ?',
  'answers': ['Inter Milan', 'AC Milan', 'Juventus', 'Roma'],
  'correct': 'Inter Milan'},
 {'question': 'Quel club espagnol a remporté 1992 European Cup ?',
  'answers': ['Barcelona', 'Real Madrid', 'Valencia', 'Atlético Madrid'],
  'correct': 'Barcelona'},
 {'question': 'Quel club était surnommé les « Invincibles » lors de la saison de Premier League '
              '2003-04 ?',
  'answers': ['Arsenal', 'Chelsea', 'Manchester United', 'Liverpool'],
  'correct': 'Arsenal'},
 {'question': 'Quel club a remporté la Ligue des champions de l’UEFA 2010 après un triplé italien '
              '?',
  'answers': ['Inter Milan', 'AC Milan', 'Juventus', 'Roma'],
  'correct': 'Inter Milan'},
 {'question': 'Quel club a remporté le premier titre de Premier League en 1992-93 ?',
  'answers': ['Manchester United', 'Blackburn Rovers', 'Arsenal', 'Chelsea'],
  'correct': 'Manchester United'},
 {'question': 'Quel club a remporté la Premier League en 1994-95 ?',
  'answers': ['Blackburn Rovers', 'Manchester United', 'Arsenal', 'Newcastle United'],
  'correct': 'Blackburn Rovers'},
 {'question': 'Quel club a remporté la Premier League 2003-04 sans perdre un seul match ?',
  'answers': ['Arsenal', 'Manchester United', 'Chelsea', 'Liverpool'],
  'correct': 'Arsenal'},
 {'question': 'Qui est surnommé le « Roi égyptien » ?',
  'answers': ['Mohamed Salah', 'Riyad Mahrez', 'Sadio Mané', 'Didier Drogba'],
  'correct': 'Mohamed Salah'},
 {'question': 'Quel club joue ses matchs à domicile à Anfield ?',
  'answers': ['Liverpool', 'Everton', 'Manchester City', 'Chelsea'],
  'correct': 'Liverpool'},
 {'question': 'Quel club joue ses matchs à domicile à Old Trafford ?',
  'answers': ['Manchester United', 'Manchester City', 'Liverpool', 'Arsenal'],
  'correct': 'Manchester United'},
 {'question': 'Quel club joue ses matchs à domicile à Stamford Bridge ?',
  'answers': ['Chelsea', 'Fulham', 'West Ham United', 'Tottenham Hotspur'],
  'correct': 'Chelsea'},
 {'question': 'Quel club joue ses matchs à domicile à the Emirates Stadium ?',
  'answers': ['Arsenal', 'Tottenham Hotspur', 'Chelsea', 'West Ham United'],
  'correct': 'Arsenal'},
 {'question': 'Quel club joue ses matchs à domicile à the Etihad Stadium ?',
  'answers': ['Manchester City', 'Manchester United', 'Everton', 'Liverpool'],
  'correct': 'Manchester City'},
 {'question': 'Quel club joue ses matchs à domicile à Goodison Park ?',
  'answers': ['Everton', 'Liverpool', 'Newcastle United', 'West Ham United'],
  'correct': 'Everton'},
 {'question': "Quel club est basé à St James' Park ?",
  'answers': ['Newcastle United', 'Sunderland', 'Aston Villa', 'Leicester City'],
  'correct': 'Newcastle United'},
 {'question': 'Quel club est surnommé les « Red Devils » ?',
  'answers': ['Manchester United', 'Liverpool', 'Arsenal', 'Chelsea'],
  'correct': 'Manchester United'},
 {'question': 'Quel club est surnommé les « Blues » en Premier League ?',
  'answers': ['Chelsea', 'Everton', 'Manchester City', 'Leicester City'],
  'correct': 'Chelsea'},
 {'question': 'Quel club est surnommé les « Gunners » ?',
  'answers': ['Arsenal', 'Liverpool', 'Tottenham Hotspur', 'West Ham United'],
  'correct': 'Arsenal'},
 {'question': 'Quel club est surnommé les « Reds » ?',
  'answers': ['Liverpool', 'Manchester United', 'Nottingham Forest', 'Brentford'],
  'correct': 'Liverpool'},
 {'question': 'Quel club a remporté la Premier League en 2015-16 against the odds ?',
  'answers': ['Leicester City', 'Tottenham Hotspur', 'West Ham United', 'Everton'],
  'correct': 'Leicester City'},
 {'question': 'Quel club a remporté la Premier League en 2004-05 ?',
  'answers': ['Chelsea', 'Arsenal', 'Manchester United', 'Liverpool'],
  'correct': 'Chelsea'},
 {'question': 'Quel club a remporté la Premier League en 2011-12 ?',
  'answers': ['Manchester City', 'Manchester United', 'Chelsea', 'Arsenal'],
  'correct': 'Manchester City'},
 {'question': 'Quel club a remporté la Premier League en 2013-14 ?',
  'answers': ['Manchester City', 'Liverpool', 'Chelsea', 'Manchester United'],
  'correct': 'Manchester City'},
 {'question': 'Quel club a remporté la Premier League en 2016-17 ?',
  'answers': ['Chelsea', 'Tottenham Hotspur', 'Manchester City', 'Arsenal'],
  'correct': 'Chelsea'},
 {'question': 'Quel club a remporté la Premier League en 2019-20 ?',
  'answers': ['Liverpool', 'Manchester City', 'Chelsea', 'Leicester City'],
  'correct': 'Liverpool'},
 {'question': 'Quel club a remporté la Premier League en 2020-21 ?',
  'answers': ['Manchester City', 'Manchester United', 'Liverpool', 'Chelsea'],
  'correct': 'Manchester City'},
 {'question': 'Quel club a remporté la Premier League en 2021-22 ?',
  'answers': ['Manchester City', 'Liverpool', 'Chelsea', 'Arsenal'],
  'correct': 'Manchester City'},
 {'question': 'Quel club a remporté la Premier League en 2022-23 ?',
  'answers': ['Manchester City', 'Arsenal', 'Liverpool', 'Manchester United'],
  'correct': 'Manchester City'},
 {'question': 'Quel club a remporté la Premier League en 2023-24 ?',
  'answers': ['Manchester City', 'Arsenal', 'Liverpool', 'Chelsea'],
  'correct': 'Manchester City'},
 {'question': 'Quel club joue au Camp Nou ?',
  'answers': ['Barcelona', 'Real Madrid', 'Atlético Madrid', 'Valencia'],
  'correct': 'Barcelona'},
 {'question': 'Quel club joue au Santiago Bernabéu ?',
  'answers': ['Real Madrid', 'Barcelona', 'Sevilla', 'Athletic Club'],
  'correct': 'Real Madrid'},
 {'question': 'Quel club est surnommé « Los Blancos » ?',
  'answers': ['Real Madrid', 'Barcelona', 'Atlético Madrid', 'Valencia'],
  'correct': 'Real Madrid'},
 {'question': 'Quel club est surnommé « Blaugrana » ?',
  'answers': ['Barcelona', 'Real Madrid', 'Sevilla', 'Villarreal'],
  'correct': 'Barcelona'},
 {'question': 'Quel club italien joue à San Siro ?',
  'answers': ['AC Milan and Inter Milan',
              'Juventus and Torino',
              'Roma and Lazio',
              'Napoli and Salernitana'],
  'correct': 'AC Milan and Inter Milan'},
 {'question': 'Quel club joue à l’Allianz Stadium de Turin ?',
  'answers': ['Juventus', 'Torino', 'Inter Milan', 'AC Milan'],
  'correct': 'Juventus'},
 {'question': 'Quel club est connu sous le nom « I Bianconeri » ?',
  'answers': ['Juventus', 'AC Milan', 'Inter Milan', 'Napoli'],
  'correct': 'Juventus'},
 {'question': 'Quel club allemand joue au Signal Iduna Park ?',
  'answers': ['Borussia Dortmund', 'Bayern Munich', 'RB Leipzig', 'Schalke 04'],
  'correct': 'Borussia Dortmund'},
 {'question': 'Quel club allemand est surnommé « Die Roten » ?',
  'answers': ['Bayern Munich', 'Borussia Dortmund', 'Bayer Leverkusen', 'Werder Bremen'],
  'correct': 'Bayern Munich'},
 {'question': 'Quel club français joue au Parc des Princes ?',
  'answers': ['Paris Saint-Germain', 'Marseille', 'Lyon', 'Monaco'],
  'correct': 'Paris Saint-Germain'},
 {'question': 'Quel club est surnommé « Les Parisiens » ?',
  'answers': ['Paris Saint-Germain', 'Marseille', 'Lyon', 'Monaco'],
  'correct': 'Paris Saint-Germain'},
 {'question': 'Quel club a remporté la Ligue des champions de l’UEFA 1995 ?',
  'answers': ['Ajax', 'AC Milan', 'Juventus', 'Barcelona'],
  'correct': 'Ajax'},
 {'question': 'Quel club a remporté la Coupe d’Europe 1983 ?',
  'answers': ['Hamburg', 'Juventus', 'Liverpool', 'Roma'],
  'correct': 'Hamburg'},
 {'question': 'Quel club a remporté la Coupe d’Europe 1984 ?',
  'answers': ['Liverpool', 'Roma', 'Juventus', 'Bayern Munich'],
  'correct': 'Liverpool'},
 {'question': 'Quel club a remporté la Coupe d’Europe 1985 ?',
  'answers': ['Juventus', 'Liverpool', 'Everton', 'Barcelona'],
  'correct': 'Juventus'},
 {'question': 'Quel pays a remporté l’Euro de l’UEFA 2004 ?',
  'answers': ['Grèce', 'Portugal', 'Espagne', 'France'],
  'correct': 'Grèce'},
 {'question': 'Quel pays a remporté l’Euro de l’UEFA 2008 ?',
  'answers': ['Espagne', 'Allemagne', 'Italie', 'Portugal'],
  'correct': 'Espagne'},
 {'question': 'Quel pays a remporté l’Euro de l’UEFA 2012 ?',
  'answers': ['Espagne', 'Italie', 'Allemagne', 'Portugal'],
  'correct': 'Espagne'},
 {'question': 'Quel pays a remporté l’Euro de l’UEFA 2016 ?',
  'answers': ['Portugal', 'France', 'Allemagne', 'Espagne'],
  'correct': 'Portugal'},
 {'question': 'Quel pays a remporté l’Euro de l’UEFA 2020 ?',
  'answers': ['Italie', 'Angleterre', 'France', 'Belgique'],
  'correct': 'Italie'},
 {'question': 'Quel pays a remporté l’Euro de l’UEFA 2024 ?',
  'answers': ['Espagne', 'Angleterre', 'Allemagne', 'France'],
  'correct': 'Espagne'},
 {'question': 'Quel pays a remporté l’Euro de l’UEFA 2000 ?',
  'answers': ['France', 'Italie', 'Pays-Bas', 'Portugal'],
  'correct': 'France'},
 {'question': 'Quel pays a remporté l’Euro de l’UEFA 1996 ?',
  'answers': ['Allemagne', 'Angleterre', 'France', 'République tchèque'],
  'correct': 'Allemagne'},
 {'question': 'Quel pays a remporté l’Euro de l’UEFA 1992 ?',
  'answers': ['Danemark', 'Allemagne', 'Suède', 'Pays-Bas'],
  'correct': 'Danemark'},
 {'question': 'Quel pays a remporté l’Euro de l’UEFA 1988 ?',
  'answers': ['Pays-Bas', 'Allemagne de l’Ouest', 'Italie', 'France'],
  'correct': 'Pays-Bas'},
 {'question': 'Quel pays a remporté l’Euro de l’UEFA 1984 ?',
  'answers': ['France', 'Espagne', 'Allemagne', 'Belgique'],
  'correct': 'France'},
 {'question': 'Quel pays a remporté l’Euro de l’UEFA 1980 ?',
  'answers': ['Allemagne de l’Ouest', 'Belgique', 'Italie', 'Pays-Bas'],
  'correct': 'Allemagne de l’Ouest'},
 {'question': 'Quel pays a remporté l’Euro de l’UEFA 1976 ?',
  'answers': ['Tchécoslovaquie', 'Allemagne de l’Ouest', 'Pays-Bas', 'France'],
  'correct': 'Tchécoslovaquie'},
 {'question': 'Quel pays a remporté l’Euro de l’UEFA 1972 ?',
  'answers': ['Allemagne de l’Ouest', 'Union soviétique', 'Belgique', 'Italie'],
  'correct': 'Allemagne de l’Ouest'},
 {'question': 'Quel pays a remporté l’Euro de l’UEFA 1968 ?',
  'answers': ['Italie', 'Yougoslavie', 'Union soviétique', 'Angleterre'],
  'correct': 'Italie'},
 {'question': 'Quel pays a remporté l’Euro de l’UEFA 1964 ?',
  'answers': ['Espagne', 'Union soviétique', 'Hungary', 'France'],
  'correct': 'Espagne'},
 {'question': 'Quel pays a remporté le premier Championnat d’Europe en 1960 ?',
  'answers': ['Union soviétique', 'Yougoslavie', 'Espagne', 'France'],
  'correct': 'Union soviétique'},
 {'question': 'Quel pays a accueilli et remporté l’Euro de l’UEFA 1984 ?',
  'answers': ['France', 'Espagne', 'Allemagne', 'Italie'],
  'correct': 'France'},
 {'question': 'Quelle équipe nationale est surnommée « Azzurri » ?',
  'answers': ['Italie', 'France', 'Espagne', 'Croatie'],
  'correct': 'Italie'},
 {'question': 'Quelle équipe nationale est surnommée « La Roja » ?',
  'answers': ['Espagne', 'Portugal', 'Chili', 'Mexique'],
  'correct': 'Espagne'},
 {'question': 'Quel pays Cristiano Ronaldo représente-t-il ?',
  'answers': ['Portugal', 'Espagne', 'Brésil', 'Argentine'],
  'correct': 'Portugal'},
 {'question': 'Quel pays Lionel Messi représente-t-il ?',
  'answers': ['Argentine', 'Brésil', 'Uruguay', 'Espagne'],
  'correct': 'Argentine'},
 {'question': 'Quel pays Kylian Mbappé représente-t-il ?',
  'answers': ['France', 'Belgique', 'Cameroon', 'Espagne'],
  'correct': 'France'},
 {'question': 'Quel pays Erling Haaland représente-t-il ?',
  'answers': ['Norvège', 'Danemark', 'Suède', 'Finlande'],
  'correct': 'Norvège'},
 {'question': 'Quel pays Vinícius Júnior représente-t-il ?',
  'answers': ['Brésil', 'Portugal', 'Espagne', 'Colombie'],
  'correct': 'Brésil'},
 {'question': 'Quel pays Jude Bellingham représente-t-il ?',
  'answers': ['Angleterre', 'Écosse', 'Pays de Galles', 'Irlande'],
  'correct': 'Angleterre'},
 {'question': 'Quel pays Lamine Yamal représente-t-il ?',
  'answers': ['Espagne', 'Maroc', 'France', 'Brésil'],
  'correct': 'Espagne'},
 {'question': 'Quel pays Mohamed Salah représente-t-il ?',
  'answers': ['Égypte', 'Maroc', 'Algérie', 'Tunisie'],
  'correct': 'Égypte'},
 {'question': 'Quel pays Kevin De Bruyne représente-t-il ?',
  'answers': ['Belgique', 'Pays-Bas', 'Allemagne', 'France'],
  'correct': 'Belgique'},
 {'question': 'Quel pays Robert Lewandowski représente-t-il ?',
  'answers': ['Pologne', 'Allemagne', 'République tchèque', 'Ukraine'],
  'correct': 'Pologne'},
 {'question': 'Quel pays Virgil van Dijk représente-t-il ?',
  'answers': ['Pays-Bas', 'Belgique', 'Danemark', 'Suriname'],
  'correct': 'Pays-Bas'},
 {'question': 'Quel pays Achraf Hakimi représente-t-il ?',
  'answers': ['Maroc', 'Algérie', 'Tunisie', 'Égypte'],
  'correct': 'Maroc'},
 {'question': 'Quel pays Bukayo Saka représente-t-il ?',
  'answers': ['Angleterre', 'Nigeria', 'Ghana', 'Écosse'],
  'correct': 'Angleterre'},
 {'question': 'Quel pays Rodri représente-t-il ?',
  'answers': ['Espagne', 'Portugal', 'Mexique', 'Argentine'],
  'correct': 'Espagne'},
 {'question': 'Quel pays Thibaut Courtois représente-t-il ?',
  'answers': ['Belgique', 'France', 'Pays-Bas', 'Luxembourg'],
  'correct': 'Belgique'},
 {'question': 'Quel pays Alisson Becker représente-t-il ?',
  'answers': ['Brésil', 'Argentine', 'Portugal', 'Chili'],
  'correct': 'Brésil'},
 {'question': 'À quel poste Cristiano Ronaldo est-il principalement associé ?',
  'answers': ['Attaquant', 'Gardien de but', 'Défenseur', 'Milieu central'],
  'correct': 'Attaquant'},
 {'question': 'À quel poste joue Thibaut Courtois ?',
  'answers': ['Gardien de but', 'Avant-centre', 'Ailier', 'Défenseur'],
  'correct': 'Gardien de but'},
 {'question': 'À quel poste joue Virgil van Dijk ?',
  'answers': ['Défenseur central', 'Gardien de but', 'Ailier', 'Avant-centre'],
  'correct': 'Défenseur central'},
 {'question': 'À quel poste Mohamed Salah est-il principalement associé ?',
  'answers': ['Ailier/attaquant', 'Gardien de but', 'Défenseur central', 'Defensive midfielder'],
  'correct': 'Ailier/attaquant'},
 {'question': 'Dans quel club Cristiano Ronaldo jouait-il avant Real Madrid en 2009 ?',
  'answers': ['Manchester United', 'Arsenal', 'Chelsea', 'Liverpool'],
  'correct': 'Manchester United'},
 {'question': 'Dans quel club Lionel Messi a-t-il passé la majeure partie de sa carrière '
              'professionnelle ?',
  'answers': ['Barcelona', 'Real Madrid', 'Atlético Madrid', 'Sevilla'],
  'correct': 'Barcelona'},
 {'question': 'Quel club Neymar a-t-il rejoint en provenance de Santos en 2013 ?',
  'answers': ['Barcelona', 'Real Madrid', 'Paris Saint-Germain', 'Chelsea'],
  'correct': 'Barcelona'},
 {'question': 'Quel club Kylian Mbappé a-t-il rejoint en provenance de Monaco en 2017 ?',
  'answers': ['Paris Saint-Germain', 'Real Madrid', 'Manchester City', 'Lyon'],
  'correct': 'Paris Saint-Germain'},
 {'question': 'Quel club Erling Haaland a-t-il rejoint en provenance de Borussia Dortmund en 2022 '
              '?',
  'answers': ['Manchester City', 'Chelsea', 'Liverpool', 'Arsenal'],
  'correct': 'Manchester City'},
 {'question': 'Quel club Jude Bellingham a-t-il rejoint en provenance de Borussia Dortmund en 2023 '
              '?',
  'answers': ['Real Madrid', 'Chelsea', 'Bayern Munich', 'Manchester City'],
  'correct': 'Real Madrid'},
 {'question': 'Quel club Vinícius Júnior a-t-il rejoint en Europe ?',
  'answers': ['Real Madrid', 'Barcelona', 'Sevilla', 'Valencia'],
  'correct': 'Real Madrid'},
 {'question': 'Quel club Robert Lewandowski a-t-il rejoint en provenance de Bayern Munich en 2022 '
              '?',
  'answers': ['Barcelona', 'Real Madrid', 'Inter Milan', 'Paris Saint-Germain'],
  'correct': 'Barcelona'},
 {'question': 'Quel club Mohamed Salah a-t-il rejoint en 2017 ?',
  'answers': ['Liverpool', 'Chelsea', 'Manchester United', 'Arsenal'],
  'correct': 'Liverpool'},
 {'question': 'Quel club Kevin De Bruyne a-t-il rejoint en 2015 ?',
  'answers': ['Manchester City', 'Chelsea', 'Liverpool', 'Tottenham Hotspur'],
  'correct': 'Manchester City'},
 {'question': 'Quel club Rodri a-t-il rejoint en 2019 ?',
  'answers': ['Manchester City', 'Atlético Madrid', 'Barcelona', 'Real Madrid'],
  'correct': 'Manchester City'},
 {'question': 'Quel club Achraf Hakimi a-t-il rejoint en 2021 ?',
  'answers': ['Paris Saint-Germain', 'Chelsea', 'Inter Milan', 'Real Madrid'],
  'correct': 'Paris Saint-Germain'},
 {'question': 'Quel club Thibaut Courtois a-t-il rejoint en 2018 ?',
  'answers': ['Real Madrid', 'Chelsea', 'Atlético Madrid', 'Barcelona'],
  'correct': 'Real Madrid'},
 {'question': 'Quel club Alisson Becker a-t-il rejoint en 2018 ?',
  'answers': ['Liverpool', 'Chelsea', 'Manchester City', 'Arsenal'],
  'correct': 'Liverpool'},
 {'question': 'Quel club Virgil van Dijk a-t-il rejoint en janvier 2018 ?',
  'answers': ['Liverpool', 'Southampton', 'Chelsea', 'Manchester City'],
  'correct': 'Liverpool'},
 {'question': 'Quel club Harry Kane a-t-il quitté en 2023 ?',
  'answers': ['Tottenham Hotspur', 'Leicester City', 'Chelsea', 'Arsenal'],
  'correct': 'Tottenham Hotspur'},
 {'question': 'Quel club Karim Benzema a-t-il quitté en 2023 ?',
  'answers': ['Real Madrid', 'Lyon', 'Juventus', 'Inter Milan'],
  'correct': 'Real Madrid'},
 {'question': 'Quel club Sadio Mané a-t-il rejoint en 2023 ?',
  'answers': ['Al Nassr', 'Liverpool', 'Bayern Munich', 'Chelsea'],
  'correct': 'Al Nassr'},
 {'question': 'Quel club Gareth Bale a-t-il rejoint en provenance de Tottenham Hotspur en 2013 ?',
  'answers': ['Real Madrid', 'Barcelona', 'Manchester United', 'Paris Saint-Germain'],
  'correct': 'Real Madrid'},
 {'question': 'Quel club Luis Suárez a-t-il rejoint en provenance de Liverpool en 2014 ?',
  'answers': ['Barcelona', 'Atlético Madrid', 'Juventus', 'Inter Milan'],
  'correct': 'Barcelona'},
 {'question': 'Combien de joueurs une équipe compte-t-elle normalement sur le terrain ?',
  'answers': ['11', '10', '12', '9'],
  'correct': '11'},
 {'question': 'Combien de temps dure un match de football standard, hors temps additionnel ?',
  'answers': ['90 minutes', '80 minutes', '100 minutes', '120 minutes'],
  'correct': '90 minutes'},
 {'question': 'Combien de mi-temps compte un match de football standard ?',
  'answers': ['2', '3', '4', '1'],
  'correct': '2'},
 {'question': 'Combien de temps dure chaque mi-temps réglementaire ?',
  'answers': ['45 minutes', '40 minutes', '50 minutes', '35 minutes'],
  'correct': '45 minutes'},
 {'question': 'Combien de points une victoire en championnat rapporte-t-elle normalement ?',
  'answers': ['3', '2', '1', '4'],
  'correct': '3'},
 {'question': 'Combien de points un match nul rapporte-t-il normalement à chaque équipe ?',
  'answers': ['1', '3', '2', '0'],
  'correct': '1'},
 {'question': 'Quel carton signifie normalement qu’un joueur est expulsé ?',
  'answers': ['Rouge', 'Jaune', 'Bleu', 'Vert'],
  'correct': 'Rouge'},
 {'question': 'Quel carton correspond normalement à un avertissement ?',
  'answers': ['Jaune', 'Rouge', 'Bleu', 'Blanc'],
  'correct': 'Jaune'},
 {'question': 'À quel poste joue primarily responsible for stopping shots ?',
  'answers': ['Gardien de but', 'Avant-centre', 'Ailier', 'Latéral'],
  'correct': 'Gardien de but'},
 {'question': 'Quel poste joue généralement dans l’axe de la défense ?',
  'answers': ['Défenseur central', 'Ailier', 'Avant-centre', 'Gardien de but'],
  'correct': 'Défenseur central'},
 {'question': 'Quel poste joue généralement sur les côtés de la défense ?',
  'answers': ['Latéral', 'Avant-centre', 'Défenseur central', 'Gardien de but'],
  'correct': 'Latéral'},
 {'question': 'À quel poste joue usually the main central attacking role ?',
  'answers': ['Avant-centre', 'Gardien de but', 'Défenseur central', 'Latéral'],
  'correct': 'Avant-centre'},
 {'question': 'Qu’est-ce qu’un triplé ?',
  'answers': ['Trois buts inscrits par un même joueur',
              'Trois passes décisives par un même joueur',
              'Trois cartons jaunes',
              'Trois arrêts'],
  'correct': 'Trois buts inscrits par un même joueur'},
 {'question': 'Qu’est-ce qu’une clean sheet ?',
  'answers': ['Ne concéder aucun but',
              'Ne marquer aucun but',
              'Gagner avec cinq buts d’écart',
              'Avoir plus de 60 % de possession'],
  'correct': 'Ne concéder aucun but'},
 {'question': 'Que signifie VAR ?',
  'answers': ['Assistant vidéo à l’arbitrage',
              'Virtual Attack Review',
              'Video Analysis Rule',
              'Verified Assistant Replay'],
  'correct': 'Assistant vidéo à l’arbitrage'},
 {'question': 'Combien de tirs au but sont normalement tirés par équipe lors de la première série '
              'd’une séance de tirs au but ?',
  'answers': ['5', '3', '4', '6'],
  'correct': '5'},
 {'question': 'D’où est tiré un penalty ?',
  'answers': ['Point de penalty', 'Cercle central', 'Ligne des six mètres', 'Arc de corner'],
  'correct': 'Point de penalty'},
 {'question': 'Quelle remise en jeu intervient lorsque le ballon franchit la ligne de touche ?',
  'answers': ['Touche', 'Corner', 'Coup de pied de but', 'Balle à terre'],
  'correct': 'Touche'},
 {'question': 'Quelle remise en jeu intervient lorsqu’un joueur attaquant touche le ballon en '
              'dernier avant qu’il franchisse la ligne de but ?',
  'answers': ['Coup de pied de but', 'Corner', 'Touche', 'Coup franc'],
  'correct': 'Coup de pied de but'},
 {'question': 'Quelle remise en jeu intervient lorsqu’un défenseur touche le ballon en dernier '
              'avant qu’il franchisse la ligne de but ?',
  'answers': ['Corner', 'Coup de pied de but', 'Touche', 'Balle à terre'],
  'correct': 'Corner'},
 {'question': 'Quel pays est célèbre dans le football pour ses couleurs nationales jaune et bleu ?',
  'answers': ['Brésil', 'Argentine', 'Uruguay', 'Colombie'],
  'correct': 'Brésil'},
 {'question': "Quel club est célèbre pour l’hymne « You'll Never Walk Alone » ?",
  'answers': ['Liverpool', 'Arsenal', 'Chelsea', 'Everton'],
  'correct': 'Liverpool'},
 {'question': 'Quel club est célèbre pour la devise « Mia San Mia » ?',
  'answers': ['Bayern Munich', 'Borussia Dortmund', 'Bayer Leverkusen', 'Schalke 04'],
  'correct': 'Bayern Munich'},
 {'question': 'Quel club est communément appelé « Los Colchoneros » ?',
  'answers': ['Atlético Madrid', 'Real Madrid', 'Barcelona', 'Sevilla'],
  'correct': 'Atlético Madrid'},
 {'question': 'Quel club est communément appelé « The Old Lady » ?',
  'answers': ['Juventus', 'Inter Milan', 'AC Milan', 'Roma'],
  'correct': 'Juventus'},
 {'question': 'Quel club est communément appelé les « Reds » du Merseyside ?',
  'answers': ['Liverpool', 'Everton', 'Burnley', 'Leicester City'],
  'correct': 'Liverpool'},
 {'question': 'Quel club est communément appelé « The Lilywhites » ?',
  'answers': ['Tottenham Hotspur', 'Leeds United', 'Fulham', 'Southampton'],
  'correct': 'Tottenham Hotspur'},
 {'question': 'Quel club est communément appelé « The Foxes » ?',
  'answers': ['Leicester City', 'Wolves', 'Aston Villa', 'Everton'],
  'correct': 'Leicester City'},
 {'question': 'Quel club est communément appelé « The Citizens » ?',
  'answers': ['Manchester City', 'Manchester United', 'Chelsea', 'Leicester City'],
  'correct': 'Manchester City'},
 {'question': 'Quel club est communément appelé « The Hammers » ?',
  'answers': ['West Ham United', 'Newcastle United', 'Arsenal', 'Fulham'],
  'correct': 'West Ham United'},
 {'question': 'Dans quelle ville se trouve Real Madrid ?',
  'answers': ['Madrid', 'Barcelona', 'Seville', 'Valencia'],
  'correct': 'Madrid'},
 {'question': 'Dans quelle ville se trouve Liverpool FC ?',
  'answers': ['Liverpool', 'Manchester', 'Leeds', 'Birmingham'],
  'correct': 'Liverpool'},
 {'question': 'Dans quelle ville se trouve Bayern Munich ?',
  'answers': ['Munich', 'Berlin', 'Hamburg', 'Frankfurt'],
  'correct': 'Munich'},
 {'question': 'Dans quelle ville se trouve Paris Saint-Germain ?',
  'answers': ['Paris', 'Lyon', 'Marseille', 'Nice'],
  'correct': 'Paris'},
 {'question': 'Dans quelle ville se trouve Juventus ?',
  'answers': ['Turin', 'Milan', 'Rome', 'Naples'],
  'correct': 'Turin'},
 {'question': 'Dans quel pays se trouve Real Madrid ?',
  'answers': ['Espagne', 'Angleterre', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Barcelona ?',
  'answers': ['Espagne', 'Angleterre', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Atlético Madrid ?',
  'answers': ['Espagne', 'Angleterre', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Liverpool ?',
  'answers': ['Angleterre', 'Espagne', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Manchester United ?',
  'answers': ['Angleterre', 'Espagne', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Manchester City ?',
  'answers': ['Angleterre', 'Espagne', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Arsenal ?',
  'answers': ['Angleterre', 'Espagne', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Chelsea ?',
  'answers': ['Angleterre', 'Espagne', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Tottenham Hotspur ?',
  'answers': ['Angleterre', 'Espagne', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Bayern Munich ?',
  'answers': ['Allemagne', 'Espagne', 'Angleterre', 'Italie'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Borussia Dortmund ?',
  'answers': ['Allemagne', 'Espagne', 'Angleterre', 'Italie'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Bayer Leverkusen ?',
  'answers': ['Allemagne', 'Espagne', 'Angleterre', 'Italie'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Juventus ?',
  'answers': ['Italie', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve AC Milan ?',
  'answers': ['Italie', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Inter Milan ?',
  'answers': ['Italie', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Roma ?',
  'answers': ['Italie', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Paris Saint-Germain ?',
  'answers': ['France', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Marseille ?',
  'answers': ['France', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Lyon ?',
  'answers': ['France', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Monaco ?',
  'answers': ['France', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Ajax ?',
  'answers': ['Pays-Bas', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve PSV Eindhoven ?',
  'answers': ['Pays-Bas', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Porto ?',
  'answers': ['Portugal', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Benfica ?',
  'answers': ['Portugal', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Sporting CP ?',
  'answers': ['Portugal', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Galatasaray ?',
  'answers': ['Turquie', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Fenerbahçe ?',
  'answers': ['Turquie', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Celtic ?',
  'answers': ['Écosse', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Rangers ?',
  'answers': ['Écosse', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve River Plate ?',
  'answers': ['Argentine', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Boca Juniors ?',
  'answers': ['Argentine', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Flamengo ?',
  'answers': ['Brésil', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Santos ?',
  'answers': ['Brésil', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Dans quel pays se trouve Corinthians ?',
  'answers': ['Brésil', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Quel club est basé à Wembley Stadium when England play international home matches ?',
  'answers': ['Angleterre', 'Chelsea', 'Arsenal', 'Tottenham Hotspur'],
  'correct': 'Angleterre'},
 {'question': 'Quel club a été fondé en 1902 et fait partie des clubs les plus célèbres au monde ?',
  'answers': ['Real Madrid', 'Barcelona', 'Liverpool', 'Bayern Munich'],
  'correct': 'Real Madrid'},
 {'question': 'Quel club est associé à la ville de Naples ?',
  'answers': ['Napoli', 'Roma', 'Lazio', 'Fiorentina'],
  'correct': 'Napoli'},
 {'question': 'Quel club est associé à la ville de Florence ?',
  'answers': ['Fiorentina', 'Napoli', 'Roma', 'Lazio'],
  'correct': 'Fiorentina'},
 {'question': 'Quel club est associé à la ville de Rome and wears sky blue ?',
  'answers': ['Lazio', 'Roma', 'Napoli', 'Torino'],
  'correct': 'Lazio'},
 {'question': 'Quel club est associé à la ville de Rome and wears maroon and gold ?',
  'answers': ['Roma', 'Lazio', 'Napoli', 'Fiorentina'],
  'correct': 'Roma'},
 {'question': 'Quel club est associé à Marseille ?',
  'answers': ['Olympique de Marseille', 'Lyon', 'Monaco', 'Nice'],
  'correct': 'Olympique de Marseille'},
 {'question': 'Quel club est associé à Rotterdam ?',
  'answers': ['Feyenoord', 'Ajax', 'PSV', 'AZ Alkmaar'],
  'correct': 'Feyenoord'},
 {'question': 'Quel club est associé à Eindhoven ?',
  'answers': ['PSV Eindhoven', 'Ajax', 'Feyenoord', 'Twente'],
  'correct': 'PSV Eindhoven'},
 {'question': 'Quel club est associé à Glasgow et porte les couleurs vert et blanc ?',
  'answers': ['Celtic', 'Rangers', 'Hearts', 'Aberdeen'],
  'correct': 'Celtic'},
 {'question': 'Quel club est associé à Glasgow et porte le bleu ?',
  'answers': ['Rangers', 'Celtic', 'Hearts', 'Hibernian'],
  'correct': 'Rangers'},
 {'question': 'Quel club est associé à Lisbonne et porte les couleurs rouge et blanc ?',
  'answers': ['Benfica', 'Sporting CP', 'Porto', 'Braga'],
  'correct': 'Benfica'},
 {'question': 'Quel club est associé à Lisbonne et porte les couleurs vert et blanc ?',
  'answers': ['Sporting CP', 'Benfica', 'Porto', 'Braga'],
  'correct': 'Sporting CP'},
 {'question': 'Quel club est associé à Porto ?',
  'answers': ['FC Porto', 'Benfica', 'Sporting CP', 'Boavista'],
  'correct': 'FC Porto'},
 {'question': 'Quel club brésilien est célèbre pour avoir formé Pelé ?',
  'answers': ['Santos', 'Flamengo', 'Corinthians', 'Palmeiras'],
  'correct': 'Santos'},
 {'question': 'Quel club argentin est basé à La Boca ?',
  'answers': ['Boca Juniors', 'River Plate', 'Racing Club', 'Independiente'],
  'correct': 'Boca Juniors'},
 {'question': 'Quel club argentin est surnommé « Los Millonarios » ?',
  'answers': ['River Plate', 'Boca Juniors', 'Racing Club', 'San Lorenzo'],
  'correct': 'River Plate'},
 {'question': 'Quel club brésilien est basé à Rio de Janeiro et porte le rouge et noir ?',
  'answers': ['Flamengo', 'Fluminense', 'Botafogo', 'Vasco da Gama'],
  'correct': 'Flamengo'},
 {'question': 'Quel club brésilien est basé à São Paulo et est célèbre pour ses couleurs noir et '
              'blanc ?',
  'answers': ['Corinthians', 'Santos', 'Palmeiras', 'São Paulo FC'],
  'correct': 'Corinthians'},
 {'question': 'Quel club est connu pour le surnom « Rossoneri » ?',
  'answers': ['AC Milan', 'Inter Milan', 'Juventus', 'Roma'],
  'correct': 'AC Milan'},
 {'question': 'De quel pays vient le club Real Madrid ?',
  'answers': ['Espagne', 'Angleterre', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'Quel pays est représenté par le club Real Madrid ?',
  'answers': ['Espagne', 'Angleterre', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'Le club Real Madrid vient de quel pays ?',
  'answers': ['Espagne', 'Angleterre', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'De quel pays vient le club Barcelona ?',
  'answers': ['Espagne', 'Angleterre', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'Quel pays est représenté par le club Barcelona ?',
  'answers': ['Espagne', 'Angleterre', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'Le club Barcelona vient de quel pays ?',
  'answers': ['Espagne', 'Angleterre', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'De quel pays vient le club Liverpool ?',
  'answers': ['Angleterre', 'Espagne', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'Quel pays est représenté par le club Liverpool ?',
  'answers': ['Angleterre', 'Espagne', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'Le club Liverpool vient de quel pays ?',
  'answers': ['Angleterre', 'Espagne', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'De quel pays vient le club Manchester United ?',
  'answers': ['Angleterre', 'Espagne', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'Quel pays est représenté par le club Manchester United ?',
  'answers': ['Angleterre', 'Espagne', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'Le club Manchester United vient de quel pays ?',
  'answers': ['Angleterre', 'Espagne', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'De quel pays vient le club Manchester City ?',
  'answers': ['Angleterre', 'Espagne', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'Quel pays est représenté par le club Manchester City ?',
  'answers': ['Angleterre', 'Espagne', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'Le club Manchester City vient de quel pays ?',
  'answers': ['Angleterre', 'Espagne', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'De quel pays vient le club Arsenal ?',
  'answers': ['Angleterre', 'Espagne', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'Quel pays est représenté par le club Arsenal ?',
  'answers': ['Angleterre', 'Espagne', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'Le club Arsenal vient de quel pays ?',
  'answers': ['Angleterre', 'Espagne', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'De quel pays vient le club Chelsea ?',
  'answers': ['Angleterre', 'Espagne', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'Quel pays est représenté par le club Chelsea ?',
  'answers': ['Angleterre', 'Espagne', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'Le club Chelsea vient de quel pays ?',
  'answers': ['Angleterre', 'Espagne', 'Allemagne', 'Italie'],
  'correct': 0},
 {'question': 'De quel pays vient le club Bayern Munich ?',
  'answers': ['Allemagne', 'Espagne', 'Angleterre', 'Italie'],
  'correct': 0},
 {'question': 'Quel pays est représenté par le club Bayern Munich ?',
  'answers': ['Allemagne', 'Espagne', 'Angleterre', 'Italie'],
  'correct': 0},
 {'question': 'Le club Bayern Munich vient de quel pays ?',
  'answers': ['Allemagne', 'Espagne', 'Angleterre', 'Italie'],
  'correct': 0},
 {'question': 'De quel pays vient le club Borussia Dortmund ?',
  'answers': ['Allemagne', 'Espagne', 'Angleterre', 'Italie'],
  'correct': 0},
 {'question': 'Quel pays est représenté par le club Borussia Dortmund ?',
  'answers': ['Allemagne', 'Espagne', 'Angleterre', 'Italie'],
  'correct': 0},
 {'question': 'Le club Borussia Dortmund vient de quel pays ?',
  'answers': ['Allemagne', 'Espagne', 'Angleterre', 'Italie'],
  'correct': 0},
 {'question': 'De quel pays vient le club Juventus ?',
  'answers': ['Italie', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Quel pays est représenté par le club Juventus ?',
  'answers': ['Italie', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Le club Juventus vient de quel pays ?',
  'answers': ['Italie', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'De quel pays vient le club AC Milan ?',
  'answers': ['Italie', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Quel pays est représenté par le club AC Milan ?',
  'answers': ['Italie', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'Le club AC Milan vient de quel pays ?',
  'answers': ['Italie', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0},
 {'question': 'De quel pays vient le club Inter Milan ?',
  'answers': ['Italie', 'Espagne', 'Angleterre', 'Allemagne'],
  'correct': 0}]



def _question_parts(question):
    """Normalize both numeric and text-based correct answers."""
    if not isinstance(question, dict):
        raise ValueError("Invalid quiz question format.")

    question_text = str(question.get("question", "")).strip()
    answers = [str(answer) for answer in question.get("answers", [])]
    correct_value = question.get("correct")

    if not question_text or len(answers) != 4:
        raise ValueError("Every quiz question must have exactly 4 answers.")

    if isinstance(correct_value, int):
        correct_index = correct_value
    else:
        wanted = str(correct_value).strip().casefold()
        correct_index = next(
            (
                i for i, answer in enumerate(answers)
                if answer.strip().casefold() == wanted
            ),
            None,
        )

        if correct_index is None:
            raise ValueError(
                f"Correct answer {correct_value!r} was not found."
            )

    if not 0 <= correct_index < len(answers):
        raise ValueError("Correct-answer index is out of range.")

    return question_text, answers, correct_index


def _validate_question_bank(name, bank):
    if len(bank) != TOTAL_QUESTIONS:
        raise RuntimeError(
            f"{name} quiz bank mismatch: expected {TOTAL_QUESTIONS}, "
            f"found {len(bank)}."
        )

    for index, question in enumerate(bank):
        try:
            _question_parts(question)
        except Exception as error:
            raise RuntimeError(
                f"Invalid {name} quiz question #{index + 1}: {error}"
            ) from error


_validate_question_bank("English", QUESTIONS_EN)
_validate_question_bank("French", QUESTIONS_FR)



def _setting_key(template: str, user_id: int) -> str:
    return template.format(user_id=user_id)


async def _set_value(session, key: str, value: str, description: str):
    setting = await _get_setting(session, key)

    if setting is None:
        session.add(
            GameSetting(
                key=key,
                value=value,
                description=description,
            )
        )
    else:
        setting.value = value


async def _get_value(session, key: str, default=None):
    setting = await _get_setting(session, key)
    if setting is None:
        return default
    return setting.value or default


async def _get_quiz_language(session, user_id: int):
    value = await _get_value(
        session,
        _setting_key(QUIZ_LANG_KEY, user_id),
        "en",
    )
    return value if value in {"en", "fr"} else "en"


async def _set_quiz_language(session, user_id: int, language: str):
    await _set_value(
        session,
        _setting_key(QUIZ_LANG_KEY, user_id),
        language,
        "Selected language for the football quiz.",
    )
    await session.flush()


async def _set_quiz_active(session, user_id: int, active: bool):
    await _set_value(
        session,
        _setting_key(QUIZ_ACTIVE_KEY, user_id),
        "1" if active else "0",
        "Whether the user currently has an active quiz.",
    )


async def _is_quiz_active(session, user_id: int):
    value = await _get_value(
        session,
        _setting_key(QUIZ_ACTIVE_KEY, user_id),
        "0",
    )
    return value == "1"


async def _set_quiz_message(session, user_id: int, message_id: int):
    await _set_value(
        session,
        _setting_key(QUIZ_MESSAGE_KEY, user_id),
        str(message_id),
        "Telegram message ID used by the active quiz.",
    )


async def _set_quiz_chat(session, user_id: int, chat_id: int):
    await _set_value(
        session,
        _setting_key(QUIZ_CHAT_KEY, user_id),
        str(chat_id),
        "Telegram chat ID used by the active quiz.",
    )


async def _get_quiz_chat(session, user_id: int):
    value = await _get_value(
        session,
        _setting_key(QUIZ_CHAT_KEY, user_id),
    )
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


async def _get_quiz_message(session, user_id: int):
    value = await _get_value(
        session,
        _setting_key(QUIZ_MESSAGE_KEY, user_id),
    )
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


async def _set_quiz_deadline(session, user_id: int, deadline: datetime | None):
    await _set_value(
        session,
        _setting_key(QUIZ_DEADLINE_KEY, user_id),
        deadline.isoformat() if deadline else "",
        "Deadline for the current quiz question.",
    )


async def _get_quiz_deadline(session, user_id: int):
    value = await _get_value(
        session,
        _setting_key(QUIZ_DEADLINE_KEY, user_id),
    )
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


async def _get_question_bank(language: str):
    """
    Return the selected static quiz bank.
    """
    return QUESTIONS_FR if language == "fr" else QUESTIONS_EN


async def _get_question(language: str, question_id: int):
    bank = await _get_question_bank(language)

    if not 0 <= question_id < len(bank):
        raise IndexError(
            f"Quiz question ID {question_id} is out of range."
        )

    return bank[question_id]


def _language_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🇫🇷 Français",
                    callback_data="quiz:language:fr",
                ),
                InlineKeyboardButton(
                    "🇬🇧 English",
                    callback_data="quiz:language:en",
                ),
            ],
            [
                InlineKeyboardButton(
                    "❌ CLOSE",
                    callback_data="quiz:close",
                )
            ],
        ]
    )

def _quiz_language_caption():
    return (
        "🧠 𝐅𝐎𝐎𝐓𝐁𝐀𝐋𝐋 𝐐𝐔𝐈𝐙\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🌍 Choose the language for your quiz:"
    )


async def _stop_timer(user_id: int):
    task = QUIZ_TIMERS.pop(user_id, None)

    if task is not None and not task.done():
        task.cancel()


async def _timeout_question(application, user_id: int, question_id: int):
    try:
        await asyncio.sleep(QUIZ_TIME_LIMIT)

        async with AsyncSessionLocal() as session:
            if not await _is_quiz_active(session, user_id):
                return

            current = await _get_current(
                session,
                user_id,
            )

            if current != question_id:
                return

            deadline = await _get_quiz_deadline(
                session,
                user_id,
            )

            now = datetime.now(timezone.utc)

            if deadline is not None and now < deadline:
                await asyncio.sleep(
                    max(
                        0.0,
                        (deadline - now).total_seconds(),
                    )
                )

            if not await _is_quiz_active(session, user_id):
                return

            await _set_quiz_active(
                session,
                user_id,
                False,
            )
            await _set_quiz_deadline(
                session,
                user_id,
                None,
            )
            message_id = await _get_quiz_message(
                session,
                user_id,
            )
            chat_id = await _get_quiz_chat(
                session,
                user_id,
            )
            await session.commit()

        if message_id is None or chat_id is None:
            return

        try:
            await application.bot.edit_message_caption(
                chat_id=chat_id,
                message_id=message_id,
                caption=(
                    "⏰ 𝐓𝐈𝐌𝐄 𝐄𝐂𝐎𝐔𝐋𝐄\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    "The 15 seconds have expired.\n"
                    "❌ Quiz stopped.\n\n"
                    "Use /quiz to start again."
                ),
                reply_markup=None,
            )
        except Exception as error:
            if "Message is not modified" not in str(error):
                print(
                    "⚠️ QUIZ TIMEOUT EDIT ERROR:",
                    type(error).__name__,
                    error,
                )

    except asyncio.CancelledError:
        return
    except Exception as error:
        print(
            "⚠️ QUIZ TIMER ERROR:",
            type(error).__name__,
            error,
        )
    finally:
        task = QUIZ_TIMERS.get(user_id)
        if task is asyncio.current_task():
            QUIZ_TIMERS.pop(user_id, None)


async def _start_timer(application, user_id: int, question_id: int):
    await _stop_timer(user_id)

    task = asyncio.create_task(
        _timeout_question(
            application,
            user_id,
            question_id,
        )
    )

    QUIZ_TIMERS[user_id] = task


def _seen_key(user_id: int) -> str:
    return f"quiz_seen:{user_id}"


def _current_key(user_id: int) -> str:
    return f"quiz_current:{user_id}"


async def _get_user(session, user_id: int):
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def _get_setting(session, key: str):
    result = await session.execute(
        select(GameSetting).where(GameSetting.key == key)
    )
    return result.scalar_one_or_none()


async def _get_seen(session, user_id: int) -> set[int]:
    setting = await _get_setting(
        session,
        _seen_key(user_id),
    )
    if setting is None or not setting.value:
        return set()

    seen = set()
    for part in setting.value.split(","):
        try:
            seen.add(int(part))
        except ValueError:
            pass

    return seen


async def _save_seen(session, user_id: int, seen: set[int]):
    key = _seen_key(user_id)
    value = ",".join(
        str(x) for x in sorted(seen)
    )

    setting = await _get_setting(session, key)

    if setting is None:
        session.add(
            GameSetting(
                key=key,
                value=value,
                description="Quiz questions seen by this user.",
            )
        )
    else:
        setting.value = value


async def _save_current(session, user_id: int, question_id: int):
    key = _current_key(user_id)
    setting = await _get_setting(session, key)

    value = str(question_id)

    if setting is None:
        session.add(
            GameSetting(
                key=key,
                value=value,
                description="Current quiz question for this user.",
            )
        )
    else:
        setting.value = value


async def _get_current(session, user_id: int):
    setting = await _get_setting(
        session,
        _current_key(user_id),
    )
    if setting is None:
        return None

    try:
        return int(setting.value)
    except ValueError:
        return None


def _quiz_keyboard(question_id: int, answers):
    """
    Shuffle the four answer positions for this question.

    The callback keeps the ORIGINAL answer index, so shuffling the visible
    buttons never changes which answer is actually correct.
    """
    positions = list(range(len(answers)))
    random.shuffle(positions)

    rows = []

    for original_index in positions:
        rows.append(
            [
                InlineKeyboardButton(
                    str(answers[original_index]),
                    callback_data=(
                        f"quiz:answer:{question_id}:{original_index}"
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                "❌ CLOSE",
                callback_data="quiz:close",
            )
        ]
    )

    return InlineKeyboardMarkup(rows)


def _next_unseen(seen: set[int]):
    available = [
        i
        for i in range(TOTAL_QUESTIONS)
        if i not in seen
    ]

    if not available:
        # The player completed the entire bank.
        return None

    return random.choice(available)


async def _send_question(message, user_id: int, application):
    async with AsyncSessionLocal() as session:
        seen = await _get_seen(session, user_id)
        question_id = _next_unseen(seen)
        if question_id is None:
            seen.clear()
            question_id = _next_unseen(seen)

        language = await _get_quiz_language(session, user_id)
        await _save_current(session, user_id, question_id)
        await _set_quiz_active(session, user_id, True)
        await session.commit()

    question = await _get_question(language, question_id)
    question_text, answers, _ = _question_parts(question)

    if language == "fr":
        caption = (
            "🧠 𝐐𝐔𝐈𝐙 𝐃𝐄 𝐅𝐎𝐎𝐓𝐁𝐀𝐋𝐋\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"❓ {question_text}\n\n"
            f"⏳ {QUIZ_TIME_LIMIT}s\n"
            f"🎁 +{QUIZ_REWARD:,} Coins"
        )
    else:
        caption = (
            "🧠 𝐅𝐎𝐎𝐓𝐁𝐀𝐋𝐋 𝐐𝐔𝐈𝐙\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"❓ {question_text}\n\n"
            f"⏳ {QUIZ_TIME_LIMIT}s\n"
            f"🎁 +{QUIZ_REWARD:,} Coins"
        )

    # Edit the existing quiz message whenever possible. This avoids creating
    # a second message for every question.
    try:
        sent = await message.edit_caption(
            caption=caption,
            reply_markup=_quiz_keyboard(question_id, answers),
        )
    except Exception as error:
        if "Message is not modified" in str(error):
            sent = message
        else:
            sent = await message.reply_photo(
                photo=open(IMAGE_FILE, "rb"),
                caption=caption,
                reply_markup=_quiz_keyboard(question_id, answers),
            )

    # IMPORTANT: start the 20-second deadline only AFTER the question has
    # actually been rendered. Translation/database latency must not consume
    # the player's time.
    deadline = datetime.now(timezone.utc) + timedelta(seconds=QUIZ_TIME_LIMIT)

    async with AsyncSessionLocal() as session:
        await _set_quiz_message(session, user_id, sent.message_id)
        await _set_quiz_chat(session, user_id, sent.chat_id)
        await _set_quiz_deadline(session, user_id, deadline)
        await _set_quiz_active(session, user_id, True)
        await session.commit()

    await _start_timer(application, user_id, question_id)


async def quiz(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    async with AsyncSessionLocal() as session:
        db_user = await _get_user(
            session,
            user.id,
        )

        if db_user is None:
            await message.reply_text(
                "❌ Your account was not found. Use /start first."
            )
            return

        # /quiz always starts a fresh session and therefore always asks
        # for the language again.
        await _stop_timer(user.id)
        await _set_quiz_active(
            session,
            user.id,
            False,
        )
        await _set_quiz_deadline(
            session,
            user.id,
            None,
        )
        await session.commit()

    sent = await message.reply_photo(
        photo=open(IMAGE_FILE, "rb"),
        caption=_quiz_language_caption(),
        reply_markup=_language_keyboard(),
    )

    async with AsyncSessionLocal() as session:
        await _set_quiz_message(
            session,
            user.id,
            sent.message_id,
        )
        await _set_quiz_chat(
            session,
            user.id,
            sent.chat_id,
        )
        await session.commit()


async def quiz_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if (
        query is None
        or not query.data
        or query.from_user is None
    ):
        return

    try:
        await query.answer()
    except Exception:
        pass

    parts = str(query.data).split(":")

    if len(parts) >= 2 and parts[1] == "close":
        await _stop_timer(query.from_user.id)

        async with AsyncSessionLocal() as session:
            await _set_quiz_active(
                session,
                query.from_user.id,
                False,
            )
            await _set_quiz_deadline(
                session,
                query.from_user.id,
                None,
            )
            await session.commit()

        try:
            await query.message.edit_caption(
                caption="🧠 Quiz closed.",
                reply_markup=None,
            )
        except Exception as error:
            if "Message is not modified" not in str(error):
                print(
                    "⚠️ QUIZ CLOSE ERROR:",
                    type(error).__name__,
                    error,
                )
        return

    # ---------------------------------------------------------
    # LANGUAGE
    # ---------------------------------------------------------
    if (
        len(parts) == 3
        and parts[1] == "language"
        and parts[2] in {"fr", "en"}
    ):
        language = parts[2]
        user_id = query.from_user.id

        await _stop_timer(user_id)

        async with AsyncSessionLocal() as session:
            user = await _get_user(
                session,
                user_id,
            )

            if user is None:
                return

            await _set_quiz_language(
                session,
                user_id,
                language,
            )
            context.user_data["quiz_language"] = language

            await _save_seen(
                session,
                user_id,
                set(),
            )
            await _set_quiz_active(
                session,
                user_id,
                True,
            )
            await session.commit()

        await _send_question(
            query.message,
            user_id,
            context.application,
        )
        return

    # ---------------------------------------------------------
    # ANSWER
    # ---------------------------------------------------------
    if len(parts) != 4 or parts[1] != "answer":
        return

    try:
        question_id = int(parts[2])
        answer_id = int(parts[3])
    except (TypeError, ValueError):
        return

    if not 0 <= question_id < TOTAL_QUESTIONS:
        return

    user_id = query.from_user.id

    async with AsyncSessionLocal() as session:
        user = await _get_user(
            session,
            user_id,
        )

        if user is None:
            return

        if not await _is_quiz_active(
            session,
            user_id,
        ):
            return

        current = await _get_current(
            session,
            user_id,
        )

        if current != question_id:
            return

        deadline = await _get_quiz_deadline(
            session,
            user_id,
        )

        now = datetime.now(timezone.utc)

        if (
            deadline is not None
            and now >= deadline
        ):
            await _set_quiz_active(
                session,
                user_id,
                False,
            )
            await _set_quiz_deadline(
                session,
                user_id,
                None,
            )
            await session.commit()

            await _stop_timer(user_id)

            try:
                await query.message.edit_caption(
                    caption=(
                        "⏰ 𝐓𝐈𝐌𝐄 𝐄𝐂𝐎𝐔𝐋𝐄\n"
                        "━━━━━━━━━━━━━━━━━━━━\n\n"
                        "The 15 seconds have expired.\n"
                        "❌ Quiz stopped.\n\n"
                        "Use /quiz to start again."
                    ),
                    reply_markup=None,
                )
            except Exception as error:
                if "Message is not modified" not in str(error):
                    print(
                        "⚠️ QUIZ TIMEOUT CALLBACK ERROR:",
                        type(error).__name__,
                        error,
                    )
            return

        language = await _get_quiz_language(
            session,
            user_id,
        )

    question = await _get_question(
        language,
        question_id,
    )

    question_text, answers, correct_index = _question_parts(
        question
    )

    if not 0 <= answer_id < len(answers):
        return

    await _stop_timer(user_id)

    # ---------------------------------------------------------
    # WRONG ANSWER = STOP COMPLETELY
    # ---------------------------------------------------------
    if answer_id != correct_index:
        async with AsyncSessionLocal() as session:
            await _set_quiz_active(
                session,
                user_id,
                False,
            )
            await _set_quiz_deadline(
                session,
                user_id,
                None,
            )
            await session.commit()

        if language == "fr":
            caption = (
                "❌ 𝐌𝐀𝐔𝐕𝐀𝐈𝐒𝐄 𝐑É𝐏𝐎𝐍𝐒𝐄\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"✅ Bonne réponse : {answers[correct_index]}\n\n"
                "🛑 Le quiz est terminé.\n"
                "Utilise /quiz pour recommencer."
            )
        else:
            caption = (
                "❌ 𝐖𝐑𝐎𝐍𝐆 𝐀𝐍𝐒𝐖𝐄𝐑\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"✅ Correct answer : {answers[correct_index]}\n\n"
                "🛑 The quiz is over.\n"
                "Use /quiz to start again."
            )

        try:
            await query.message.edit_caption(
                caption=caption,
                reply_markup=None,
            )
        except Exception as error:
            if "Message is not modified" not in str(error):
                print(
                    "⚠️ QUIZ WRONG EDIT ERROR:",
                    type(error).__name__,
                    error,
                )
        return

    # ---------------------------------------------------------
    # CORRECT ANSWER = SHOW RESULT, THEN NEXT QUESTION
    # ---------------------------------------------------------
    async with AsyncSessionLocal() as session:
        user = await _get_user(session, user_id)
        if user is None:
            return

        user.coins += QUIZ_REWARD
        seen = await _get_seen(session, user_id)
        seen.add(question_id)
        next_id = _next_unseen(seen)

        if next_id is None:
            seen.clear()
            next_id = _next_unseen(seen)

        await _save_seen(session, user_id, seen)
        await _save_current(session, user_id, next_id)
        await _set_quiz_active(session, user_id, False)
        await _set_quiz_deadline(session, user_id, None)
        await session.commit()

    if language == "fr":
        result_caption = (
            "✅ 𝐁𝐎𝐍𝐍𝐄 𝐑É𝐏𝐎𝐍𝐒𝐄 !\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎁 +{QUIZ_REWARD:,} Coins\n"
            f"💰 Solde : {user.coins:,} Coins"
        )
    else:
        result_caption = (
            "✅ 𝐂𝐎𝐑𝐑𝐄𝐂𝐓!\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎁 +{QUIZ_REWARD:,} Coins\n"
            f"💰 Balance : {user.coins:,} Coins"
        )

    await query.message.edit_caption(
        caption=result_caption,
        reply_markup=None,
    )

    # Cancel the old question timer before displaying the result.
    await _stop_timer(user_id)

    # Keep the success result visible long enough to actually see it.
    await asyncio.sleep(1.5)

    await _send_question(
        query.message,
        user_id,
        context.application,
    )



quiz_handler = CommandHandler(
    "quiz",
    quiz,
)

quiz_callback_handler = CallbackQueryHandler(
    quiz_callback,
    pattern=r"^quiz:(language:(fr|en)|answer:\d+:\d+|close)$",
)