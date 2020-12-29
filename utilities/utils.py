import re
import os
import sys
from pathlib import Path
import subprocess
import requests
from inquirer import list_input

FORBIDDEN_CHARACTERS = [":", "\\", "\/", "*", "\"", "\<", "\>", "\|"]
ffmpeg = Path.cwd() / Path('ffmpeg','ffmpeg.exe')



def ask_episodes_numbers(show_title: str, num_of_episodes: int, first_episode_num: int, last_episode_num: int) -> list:
    #in case there's only one episode to download
    if first_episode_num == last_episode_num:
        return [first_episode_num]

    choice = list_options(f'{show_title} ha {num_of_episodes} episodi. Vuoi scaricarli tutti?', ['Si', 'No'])
    if choice == 'Si':
        return list(range(first_episode_num, last_episode_num+1))

    print(f"Il primo episodio e' il numero {first_episode_num}, l'ultimo e' il numero {last_episode_num}.")
    print("Inserisci i numeri degli episodi separati da una virgola. Es. 1,6,12")

    episodes_numbers = None
    while not episodes_numbers:
        try:
            episodes_numbers = input('Inserisci il numero degli episodi: ')
            if not episodes_numbers:
                print('Inserisci almeno un episodio.')
                continue
        except KeyboardInterrupt:
            exit()

        episodes_numbers = episodes_numbers.split(',')
        episodes_numbers = try_list_to_int(episodes_numbers)
        if not episodes_numbers:
            print('Inserisci solo numeri interi.')
            continue
        out_of_range = is_out_of_range(episodes_numbers, first_episode_num, last_episode_num)
        if out_of_range:
            episodes_numbers = None
    
    episodes_numbers.sort() #in case numbers have been entered like 5,2,9,6
    return episodes_numbers



def try_list_to_int(given_list: list) -> list:
    """ Tries casting to int each element of the list passed as argument. Returns the list converted to int
        if no exception is raised, otherwise returns None. """
    try:
        converted_list = [int(number) for number in given_list]
    except ValueError:
        converted_list = None

    return converted_list



def is_out_of_range(given_list: list, first_num: int, last_num: int) -> bool:
    """ If any of the elements of the list is not in between the two numbers passed as argument, returns
        that element. Otherwise returns None. """
    out_of_range = False
    for number in given_list:
        if number not in range(first_num, last_num+1):
            out_of_range = True
            print(f"L'episodio {number} non e' in lista.")
            break
        
    return out_of_range



def download(show_title: str, episode_num: str, url: str, download_path: Path, only_one = False) -> Path:
    """ Downloads episode from given url and returns its Path if download was successful, otherwise returns None. """
    show_title = format_filename(show_title)
    download_path = download_path / Path(show_title)
    if not only_one:
        episode_name = f"{show_title}_EP{episode_num}.mp4"
    else:
        episode_name = f"{show_title}.mp4"
    
    ep_download_path = download_path / Path(episode_name)
    if ep_download_path.is_file():
        choice = list_options(f"Esiste gia' un file {episode_name}. Vuoi sovrascriverlo?", ['Si', 'No'])
        if choice == 'No':
            return

    os.makedirs(download_path, exist_ok=True)
    
    print("\n" + episode_name + " downloading...")
    if url.endswith('.mp4'):
        download_success = download_mp4(url, ep_download_path)
    else:
        download_success = convert_to_mp4(url, ep_download_path)
    
    if download_success == 0:
        print(f"{episode_name} scaricato!\n")
    else:
        print(f"Il download di {episode_num} e' fallito.")
        download_path = None

    return download_path



def prepare_download(show_title: str, episode_num: str, download_path: Path, only_one: bool) -> str:
    """ Creates the directory if it doesn't already exist and creates the episode's filename, then returns the filename. """
    if not only_one:
        episode_name = f"{show_title}_EP{episode_num}.mp4"
    else:
        episode_name = f"{show_title}.mp4"
    os.makedirs(download_path, exist_ok=True)

    return episode_name



def download_mp4(url: str, ep_download_path: Path) -> int:
    """ Downloads an mp4 file from given url. Returns 0 if download was successful, 1 if it failed. """
    status_code = 0
    try:
        with requests.get(url, stream=True) as response:
            response.raise_for_status()
            file_size = int(response.headers['content-length'])
            progress = 0
            with open(ep_download_path, "wb") as file:
                for chunk in response.iter_content(chunk_size = 1024 * 1024):
                    if chunk:
                        progress += len(chunk) * 100 / file_size
                        sys.stdout.write(f"\r{int(progress)}% completato.")
                        file.write(chunk)
        print("\r100% completato.")
    except:
        status_code = 1

    return status_code



def convert_to_mp4(url: str, ep_download_path: Path) -> int:
    """ Tries to convert and download video from given url to mp4. Returns 0 if download was successful,
        1 if it failed. """
    success_code = subprocess.run([
                ffmpeg,
                "-loglevel",
                "fatal",
                "-i",
                url,
                "-c",
                "copy",
                "-bsf:a",
                "aac_adtstoasc",
                str(ep_download_path),
                "-y"])
    
    return success_code.returncode



def format_filename(name: str) -> str:
    """ Formats given string as a valid filename for Windows and Linux and returns it. """
    for i in FORBIDDEN_CHARACTERS:
        name = name.replace(i, '')

    name = name.replace(' ', '_')
    if len(name) > 175:
        name = name[:175]
    
    return name



def list_options(text: str, options: list) -> str:
    try:
        choice = list_input(text, choices=options)
    except KeyboardInterrupt:
        exit()
    
    return choice
