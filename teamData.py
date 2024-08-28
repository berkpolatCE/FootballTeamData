import requests
import re
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36'
}


def get_team_page_url(team_name):
    response = requests.get(f"https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche?query={team_name}",headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        vereine_header = soup.find('h2', string='Clubs')
        if vereine_header:
            club_result = vereine_header.find_next('td', class_='hauptlink')
            if club_result:
                link = club_result.find('a', href=True)
                if link:
                    return "https://www.transfermarkt.com" + link['href']

        all_results = soup.find_all('td', class_='hauptlink')
        for result in all_results:
            link = result.find('a', href=True)
            if link and 'verein' in link['href']:
                return "https://www.transfermarkt.com" + link['href']

        print("Couldn't find a matching club.")
        return None
    else:
        print(f"[get_team_page_url] GET request failed. Status Code: {response.status_code}")
        return None


def print_team_details(team_page_url):
    response = requests.get(url=team_page_url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        team_name = soup.find('h1', class_="data-header__headline-wrapper data-header__headline-wrapper--oswald").get_text(strip=True)
        team_league = soup.find('div', class_="data-header__club-info").find('span', class_="data-header__club").get_text(strip=True)

        team_market_value = soup.find('a', class_="data-header__market-value-wrapper").get_text(strip=True)
        team_market_value = team_market_value[:team_market_value.find('T')]

        print(f"{team_name} ({team_league})")
        print("------------------------------------------------------------------")
        print(f"     -Market Value: {team_market_value}")

        basic_team_details = soup.find('div', class_="data-header__details").find_all('li', class_='data-header__label')
        for info in basic_team_details:
            text = info.get_text(strip=True)
            if text.find('Foreigners') != -1:
                text = re.sub(r'(\d{1,2})(\d+\.\d+ %)', r'\1 (\2)', text)
                print("     -" + text)
            elif text.find('Stadium') != -1:
                text = re.sub(r'(\D)(\d[\d.]* Seats)', r'\1 (\2)', text)
                print("     -" + text)
            else:
                print("     -" + text)
        print("------------------------------------------------------------------")
    else:
        print(f"[get_team_details] GET request failed. Status Code: {response.status_code}")


def get_player_details(player_page_url):
    response = requests.get(player_page_url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        player_details = {}

        name_number = soup.find('h1', class_="data-header__headline-wrapper").get_text(strip=True)

        match = re.match(r'#(\d+)\s*(.*)', name_number)
        if match:
            number, name = match.groups()
            name = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', name)
            player_details['name'] = name
            player_details['shirt_number'] = number

        info_table = soup.find('div', class_="info-table")

        details_to_extract = {
            'Date of birth/Age:': 'dob_age',
            'Height:': 'height',
            'Citizenship:': 'citizenship',
            'Foot:': 'dominant_foot',
            'Position:': 'position'
        }

        for label, key in details_to_extract.items():
            try:
                if key == 'citizenship':
                    citizenship_span = info_table.find('span', string=label).find_next('span', class_="info-table__content info-table__content--bold")
                    nationalities = [img['alt'] for img in citizenship_span.find_all('img', class_='flaggenrahmen')]
                    value = ' / '.join(nationalities)
                else:
                    value = info_table.find('span', string=label).find_next('span', class_="info-table__content info-table__content--bold").get_text(strip=True)
                player_details[key] = value.capitalize() if key == 'dominant_foot' else value
            except AttributeError:
                player_details[key] = "Not found"

        try:
            market_value = soup.find('a', class_="data-header__market-value-wrapper").get_text(strip=True)
            player_details['market_value'] = market_value.split('Last update')[0].strip()
        except AttributeError:
            player_details['market_value'] = "Not found"

        return player_details
    else:
        return {"error": f"GET request failed. Status Code: {response.status_code}"}


def print_players_with_details(team_page_url):
    print("\nPlayers:")

    response = requests.get(team_page_url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        player_rows = soup.find_all('tr', class_=['odd', 'even'])

        for row in player_rows:
            try:
                name_cell = row.find('td', class_='hauptlink')
                if name_cell and name_cell.find('a'):
                    name = name_cell.find('a').text.strip()
                    player_url = "https://www.transfermarkt.com" + name_cell.find('a')['href']
                else:
                    continue

                market_value_cell = row.find('td', class_='rechts hauptlink')
                market_value = market_value_cell.text.strip() if market_value_cell else "N/A"

                player_details = get_player_details(player_url)

                if 'error' not in player_details:
                    print(f"Name: {name}")
                    print(f"Position: {player_details.get('position', 'N/A')}")
                    print(f"Age: {player_details.get('dob_age', 'N/A')}")
                    print(f"Nationality: {player_details.get('citizenship', 'N/A')}")
                    print(f"Market Value: {market_value}")
                    print(f"Height: {player_details.get('height', 'N/A')}")
                    print(f"Foot: {player_details.get('dominant_foot', 'N/A')}")
                    print(f"Shirt No: {player_details.get('shirt_number', 'N/A')}")
                else:
                    print(f"Error fetching details for {name}: {player_details.get('error', 'Unknown error')}")

                print("-" * 40)
            except Exception as e:
                print(f"Error processing player: {str(e)}")
                continue
    else:
        print(f"[print_players_with_details] GET request failed. Status Code: {response.status_code}")


user_team = input("Enter team name: ")
url = get_team_page_url(user_team)
print_team_details(url)
print_players_with_details(url)

#Berk Polat