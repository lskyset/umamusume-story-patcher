import sqlite3
import os
import csv
import tkinter as tk

from tkinter import ttk
from shutil import copyfile

import UnityPy

meta_conn = sqlite3.connect('../../meta')
master_conn = sqlite3.connect('../../master/master.mdb')
m_c = meta_conn.cursor()
mdb_c = master_conn.cursor()

folders = ['translations', 'backup', 'extracted']
for folder in folders:
    try:
        os.mkdir(folder)
    except FileExistsError:
        pass


def extract_dat(data):
    name, dat, file_name, chapter, *_ = data
    path = f'../../dat/{dat[:2]}/{dat}'
    env = UnityPy.load(path)
    data = {}
    for obj in env.objects:
        if obj.type == 'MonoBehaviour' and obj.serialized_type.nodes:
            for node in obj.serialized_type.nodes:
                if node.name == 'NextBlock':
                    tree = obj.read_typetree()
                    block = tree['NextBlock'] - 1 * (tree['NextBlock'] > 0)
                    data[block] = {}
                    keep_params = ['Name', 'Text', 'ChoiceDataList']
                    for param in keep_params:
                        data[block][param] = tree[param]
    if data:
        story_data = sorted(data.items())
        story_data.append(story_data.pop(0))
        story_data.pop(0)
        story = [['Language', '日本語'], ['Path', name]]
        for index, line in story_data:
            story.append([])
            story.append(['Line', index])
            story.append(['Name', line['Name']])
            tmp_text = 'Text'
            for sub_line in line['Text'].split('\r\n'):
                story.append([tmp_text, sub_line])
                tmp_text = ''
            for choice_index, choice in enumerate(line['ChoiceDataList']):
                story.append([])
                story.append(['Choice', index])
                story.append(['Number', choice_index + 1])
                tmp_text = 'Text'
                for sub_line in choice['Text'].split('\r\n'):
                    story.append([tmp_text, sub_line])
                    tmp_text = ''
        with open(f"extracted/{chapter}-{file_name}.csv", 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(story)
            print(f"Extracted {file_name}")


def load_dat(data):
    dat, slot, fp, *_ = data
    if os.path.exists(fp):
        with open(fp, 'r', encoding='utf-8') as f:

            def save(line_data):
                line_index = int(line_data.get('Line', '0'))
                choice_index = int(line_data.get('Choice', '0'))
                story_data.setdefault(line_index, {})
                story_data.setdefault(choice_index, {})
                story_data[choice_index].setdefault('Choices', [])
                if line_index:
                    story_data[line_index] = {**story_data[line_index], **line_data}
                if choice_index:
                    story_data[choice_index]['Choices'].append(line_data)

            reader = csv.reader(f)
            story_data = {}
            line_data = {}
            last_kw = None
            for row in reader:
                data = row[(slot * 2):(slot * 2 + 2)]
                if data != ['', ''] and (data[0] or last_kw):
                    if data[0] != '':
                        last_kw = data[0]
                    if line_data.get(last_kw):
                        try:
                            line_data[last_kw] += f'\r\n{data[1]}'
                        except Exception:
                            pass
                    else:
                        try:
                            data[1] = int(data[1])
                        except ValueError:
                            pass
                        line_data[last_kw] = data[1]
                else:
                    save(line_data)
                    line_data = {}
                    last_kw = None
            save(line_data)
        path = f'../../dat/{dat[:2]}/{dat}'
        backup = f'backup/{dat}'
        if not os.path.exists(backup):
            copyfile(path, backup)
        env = UnityPy.load(backup)
        for obj in env.objects:
            if obj.type == 'MonoBehaviour' and obj.serialized_type.nodes:
                for node in obj.serialized_type.nodes:
                    if node.name == 'NextBlock':
                        tree = obj.read_typetree()
                        block = tree['NextBlock'] - 1 * (tree['NextBlock'] > 0)
                        if story_data.get(block):
                            tree = {**tree, **story_data[block]}
                            for choice in story_data[block].get('Choices', []):
                                try:
                                    choice_index = choice.get('Number') - 1
                                    tree['ChoiceDataList'][choice_index] = {**tree['ChoiceDataList'][choice_index], **choice}
                                except IndexError:
                                    pass
                            if len(story_data[block].get('Text', '')) > 120:
                                tree['Size'] = 2
                            obj.save_typetree(tree)
        with open(path, "wb") as f:
            f.write(env.file.save())


def extract_story(data):
    name, chapter, story_id, *_ = data
    story_id = str(story_id)
    story_id = '0' * (9 - len(story_id)) + story_id
    dat = m_c.execute(f"select n,h from a where n LIKE '%storytimeline_{story_id}'").fetchone()
    dat = list(dat) + [name, chapter]
    extract_dat(dat)


def load_story(data):
    meta_path, slot, file_path = data
    dat = m_c.execute(f"select h from a where n LIKE '{meta_path}'").fetchone()
    dat = list(dat) + [slot, file_path]
    load_dat(dat)


def backup_restore():
    progress['value'] = 0
    frame.update_idletasks()
    dat_list = os.listdir('backup')
    length = len(dat_list)
    for i, dat in enumerate(dat_list):
        path = f'../../dat/{dat[:2]}/{dat}'
        backup = f'backup/{dat}'
        copyfile(backup, path)
        os.remove(backup)
        print(f'restored {dat}')
        progress['value'] = ((i + 1) / length) * 100
        frame.update_idletasks()


def treeview_sort_column(tv, col, reverse):
    l = [(tv.set(k, col), k) for k in tv.get_children('')]
    l.sort(reverse=reverse)
    for index, (val, k) in enumerate(l):
        tv.move(k, '', index)
    tv.heading(col, command=lambda: treeview_sort_column(tv, col, not reverse))


root = tk.Tk()
root.title('Uma Musume Story Patcher (Alpha)')
root.iconphoto(False, tk.PhotoImage(file='utx_ico_home_umamusume_12.png'))
root.geometry('900x600')
root.minsize(600, 400)

nav = tk.Frame(root)
nav.pack(side='top', fill='both')


frame = tk.Frame(root)
frame.pack(fill='both', expand=True)
frame.columnconfigure(0, weight=1)
frame.rowconfigure(0, weight=1)

notebook = ttk.Notebook(frame)
notebook.pack(fill='both', expand=True)

story_types = [
    {'id': 112, 'name': 'Main Story', 'sub_id': 94, 'table': 'main_story_data', 'select': 'part_id, id, story_number, story_id_1', 'where': 'where story_number != 0'},
    {'id': 189, 'name': 'Event Story', 'sub_id': 191, 'table': 'story_event_story_data', 'select': 'story_event_id, id, episode_index_id, story_id_1'},
    {'id': 182, 'name': 'Chara Story', 'sub_id': 92, 'table': 'chara_story_data', 'select': 'chara_id, story_id, episode_index, story_id'},
    {'id': 182, 'name': 'Training Chara Story', 'sub_id': 181, 'table': 'single_mode_story_data', 'select': 'card_chara_id, story_id, show_progress_1, story_id', 'where': 'where card_chara_id != 0'},
]

trees = []

for story_type in story_types:

    story_names = mdb_c.execute(f"Select [index], text from text_data where id = {story_type.get('id', '0')}").fetchall()
    episode_names = mdb_c.execute(f"Select [index], text from text_data where id = {story_type.get('sub_id', '0')}").fetchall()
    episodes = mdb_c.execute(f"Select {story_type.get('select')} from {story_type.get('table')} {story_type.get('where', '')}").fetchall()
    story_names = {id_: name for id_, name in story_names}
    episode_names = {id_: name for id_, name in episode_names}

    tab_frame = tk.Frame(notebook)
    tab_frame.pack(fill='both', expand=True)
    tab_frame.columnconfigure(0, weight=1)
    tab_frame.rowconfigure(0, weight=1)

    notebook.add(tab_frame, text=story_type['name'])

    cols = ('#0', 'Episode', 'Story id', 'Status')
    tree = ttk.Treeview(tab_frame, selectmode='extended', columns=cols[1:])
    for col in cols:
        txt = col
        if col == '#0':
            txt = 'Name'
        tree.heading(col, text=txt, anchor='w', command=lambda _col=col: treeview_sort_column(tree, _col, False))
        tree.column(col, minwidth=0, stretch=False)
    tree.column(cols[0], width=250)
    tree.column(cols[1], width=70)
    tree.column(cols[2], width=100)
    tree.column(cols[3], width=100)
    for id_, name in story_names.items():
        tree.insert('', tk.END, open=False, iid=id_, text=name)
    for parent, id_, *values in episodes:
        try:
            tree.insert(parent, tk.END, iid=id_, text=episode_names[id_], values=(*values,))
        except tk.TclError:
            pass
    tree.grid(row=0, column=0, sticky='NSEW')

    vsb = ttk.Scrollbar(tab_frame, orient="vertical", command=tree.yview)
    vsb.grid(row=0, column=1, rowspan=2, sticky='NSEW')
    tree.configure(yscrollcommand=vsb.set)

    hsb = ttk.Scrollbar(tab_frame, orient="horizontal", command=tree.xview)
    hsb.grid(row=1, column=0, sticky='NSEW')
    tree.configure(xscrollcommand=hsb.set)

    trees.append(tree)

progress = ttk.Progressbar(frame, orient='horizontal', length=100, mode='determinate')
progress.pack(fill='x')


def extractStories():
    tree = trees[notebook.index('current')]
    curItems = tree.selection()
    progress['value'] = 0
    frame.update_idletasks()
    length = len(curItems)
    for i, item in enumerate(curItems):
        try:
            if tree.item(item)['values']:
                data = [tree.item(item)['text']] + tree.item(item)['values']
                extract_story(data)
        except Exception as e:
            print(f'Error in extractStories {e}')
        progress['value'] = ((i + 1) / length) * 100
        frame.update_idletasks()


btn_extract = ttk.Button(nav, text='Extract selected')
btn_extract.pack(side='left')
btn_extract.configure(command=extractStories)


def loadStories():
    progress['value'] = 0
    frame.update_idletasks()
    count = 0
    cur = 0
    for root, subdirs, files in os.walk('translations'):
        count += len(files)
    for root, subdirs, files in os.walk('translations'):
        for file in files:
            cur += 1
            if file.endswith('.csv'):
                fp = os.path.join(root, file)
                with open(fp, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    metadata = {}
                    last_kw = None
                    done = {}
                    for row in reader:
                        total_slots = len(row) // 2
                        if len(done) == total_slots:
                            break
                        for slot in range(total_slots):
                            slot_data = row[(slot * 2):(slot * 2 + 2)]
                            if slot_data == ['', '']:
                                done[slot] = 'True'
                                continue
                            if done.get(slot):
                                continue
                            if slot_data[0] != '':
                                last_kw = slot_data[0]
                            if metadata.get(slot) and metadata[slot].get(last_kw):
                                metadata[slot][last_kw] = [metadata[slot][last_kw]] + [slot_data[1]]
                            else:
                                # if slot_data[0] in ['Size', 'Line']:
                                #     slot_data[1] = int(slot_data[1])
                                if not metadata.get(slot):
                                    metadata[slot] = {'Slot': slot}
                                metadata[slot][last_kw] = slot_data[1]
                    for key, settings in metadata.items():
                        lang = settings.get('Language', '')
                        if lang.lower() in ['english', 'en']:
                            try:
                                load_story((settings.get('Path'), settings.get('Slot'), fp))
                                print(f"Pathched '{file}' in {lang}")
                            except Exception as e:
                                raise e
                                print(f'Error in loadStories {e}')

            progress['value'] = ((cur + 1) / count) * 100
            frame.update_idletasks()
    progress['value'] = 100
    frame.update_idletasks()


btn_load = ttk.Button(nav, text='Patch All')
btn_load.pack(side='left')
btn_load.configure(command=loadStories)

btn_load = ttk.Button(nav, text='Restore game files')
btn_load.pack(side='left')
btn_load.configure(command=backup_restore)

root.mainloop()
