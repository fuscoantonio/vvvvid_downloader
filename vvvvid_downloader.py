'''
@author: Antonio Fusco
https://github.com/fuscoantonio
'''
import sys
sys.path.insert(1, './utilities')
from requests import Session
from requests.exceptions import HTTPError, ConnectionError
from vvvvid import real_url
from pathlib import Path
from utils import ask_episodes_numbers, download, list_options

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:80.0) Gecko/20100101 Firefox/80.0'
HEADERS = {'User-Agent': USER_AGENT}
DOWNLOAD_PATH = Path.cwd() / Path('Downloads')
is_standalone = False



def main():
    global is_standalone
    is_standalone = True
    print('### VVVVID Downloader NON ufficiale, visita vvvvid.it ###\n')
    show_id = ask_show_id()
    run(show_id)



def ask_show_id() -> str:
    show_id = -1
    while show_id < 0:
        try:
            show_id = input("Inserisci l'id dello show che vuoi scaricare: ")
            show_id = int(show_id)
            if show_id < 0:
                print("L'id non puo' essere un numero negativo.")
                continue
        except ValueError:
            print('Inserisci solo cifre numeriche e numeri interi.')
            show_id = -1
        except KeyboardInterrupt:
            exit()
    
    return str(show_id)



def run(show_id: str):
    episodes_data = request_episodes_data(show_id)
    #keeps asking for a show id if no show has been found and run() has not been called from another script
    while not episodes_data and is_standalone:
        show_id = ask_show_id()
        episodes_data = request_episodes_data(show_id)

    episodes_numbers = get_episodes_to_download(episodes_data)
    download_episodes(episodes_data, episodes_numbers)



def download_episodes(episodes_data: dict, episodes_numbers: list):
    is_any_downloaded = False
    show_title = episodes_data[0]['show_title']
    is_one_episode = len(episodes_data) == 1
    
    for number in episodes_numbers:
        episode = episodes_data[number-1]
        try:
            url = extract_url(episode)
        except Exception as e:
            print(e)
            continue
        
        episode_num = episode['number']
        download_show_path = download(show_title, episode_num, url, DOWNLOAD_PATH, is_one_episode)
        
        #if any video has been successfully downloaded it will print their path at the end
        if download_show_path is not None:
            is_any_downloaded = True

    if is_any_downloaded:
        print(f"I download si trovano in {download_show_path}")



def get_episodes_to_download(episodes_data: dict) -> list:
    if len(episodes_data) == 1:
        return [int(episodes_data[0]['number'])]

    show_title = episodes_data[0]['show_title']
    first_episode_num = int(episodes_data[0]['number'])
    last_episode_num = int(episodes_data[-1]['number'])
    chosen_episodes = ask_episodes_numbers(show_title, len(episodes_data), first_episode_num, last_episode_num)

    return chosen_episodes



def request_episodes_data(show_id: str) -> dict:
    episodes_data = None
    with Session() as session:
        try:
            conn_id = get_conn_id(session)
            show_title = get_show_title(session, show_id, conn_id)
            show_data_json = get_show_data(session, show_id, conn_id, show_title)
            season_id = get_season_id(show_data_json, show_title)
            episodes_data = get_episodes_data(session, show_id, conn_id, season_id)
        except HTTPError:
            print("### Si e' verificato un errore durante la richiesta al server. Riprova.###")
            input()
            exit()
        except ConnectionError:
            print('### Errore di connessione, verifica la tua connessione ad internet. ###')
            input()
            exit()
        except Exception as e:
            print(e)

    return episodes_data



def get_conn_id(session: Session) -> str:
    response = session.get('https://www.vvvvid.it/user/login', headers=HEADERS)
    response.raise_for_status()
    conn_id = response.json()['data']['conn_id']

    return conn_id



def get_show_title(session: Session, show_id: str, conn_id: str) -> str:
    response = session.get(f'https://www.vvvvid.it/vvvvid/ondemand/{show_id}/info/?conn_id={conn_id}', headers=HEADERS)
    response.raise_for_status()
    if response.json()['result'] == 'error':
        raise Exception(f'Non esiste uno show con id {show_id}.')

    show_title = response.json()['data']['title']

    return show_title



def get_show_data(session: Session, show_id: str, conn_id: str, show_title: str) -> dict:
    response = session.get(f'https://www.vvvvid.it/vvvvid/ondemand/{show_id}/seasons/?conn_id={conn_id}', headers=HEADERS)
    response.raise_for_status()
    show_data_json = response.json()['data']

    if len(show_data_json[0]['episodes']) == 0:
        raise Exception(f'{show_title} non ha episodi.')

    return show_data_json



def get_season_id(show_data_json, show_title: str) -> str:
    chosen_version = ask_show_version(show_data_json, show_title)
    for index, item in enumerate(show_data_json):
        if item['name'] == chosen_version:
            season_id = show_data_json[index]['episodes'][0]['season_id']
            break
    
    return season_id



def ask_show_version(show_data_json, show_title: str) -> str:
    """ Asks the user which version of the show to download if there is more than one, otherwise returns the
        only one without asking.
    """
    versions = []
    for item in show_data_json:
        versions.append(item['name'])

    chosen_version = versions[0]
    if len(versions) > 1:
        chosen_version = list_options(f'Quale versione di {show_title} vuoi scaricare?', versions)
    
    return chosen_version



def get_episodes_data(session: Session, show_id: str, conn_id: str, season_id: str) -> dict:
    """ Returns episodes json data if they have a url or are playable, otherwise raises an Exception. """
    response = session.get(f"https://www.vvvvid.it/vvvvid/ondemand/{show_id}/season/{season_id}?conn_id={conn_id}", headers=HEADERS)
    response.raise_for_status()
    episodes = response.json()['data']
    #check if none of the episodes have url or are playable
    are_not_downloadable = all(not episode['embed_info'] or not episode ['playable'] for episode in episodes)
    if are_not_downloadable:
        raise Exception("Non e' possibile scaricare questo show.")
    
    return episodes



def extract_url(episode: dict) -> str:
    """ Returns download-ready url of string type if url is present and if episode is downloadable, otherwise raises an Exception. """
    url = episode['embed_info']
    is_playable = episode['playable']
    episode_num = episode['number']
    #episode might not be playable or url might be empty
    if not is_playable or not url:
        raise Exception(f"L'episodio {episode_num} non e' scaricabile.")

    url = real_url(episode['embed_info'])
    url = format_url(url, episode['video_type'])
    if 'youtube.com' in url:
        raise Exception(f"L'episodio {episode_num} e' un video di YouTube che puoi guardare a questo url: \n{url}")

    return url



def format_url(url: str, video_type: str) -> str:
    if video_type == "video/rcs":
        url = url.replace("http:", "https:").replace(".net/z", ".net/i").replace("manifest.f4m", "master.m3u8")
    elif video_type == "video/vvvvid":
        url = url.replace(url, f"https://or01.top-ix.org/videomg/_definst_/mp4:{url}/playlist.m3u8")
    
    return url



if __name__ == '__main__':
    main()