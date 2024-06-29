import uuid
import logging
import sys
sys.path.append('../')
from database.database import Database
from database.group import GroupMessage
from database.private import PrivateMessage
from database.file import FileMessage
import base64
import os
from os.path import join, dirname, realpath
from datetime import datetime

class Chat:
    def __init__(self):
        # databases
        self.user_db = Database('user.json')
        self.group_db = Database('group.json')
        self.group_user_db = Database('group_user.json')
        self.private_message_db = Database('private_message.json')
        self.group_message_db = Database('group_message.json')
        self.file_message_db = Database('file_message.json')

        self.sessions = {}
        self.server_id = ''

    def proses(self, data, server_id):
        self.server_id = server_id
        j = data.split(" ")
        try:
            command = j[0].strip()
            if (command == 'register'):
                username = j[1].strip()
                password = j[2].strip()
                logging.warning(
                    "REGISTER: register {} {}" . format(username, password))
                return self.register_user(username, password)
            elif (command == 'auth'):
                username = j[1].strip()
                password = j[2].strip()
                logging.warning(
                    "AUTH: auth {} {}" . format(username, password))
                return self.autentikasi_user(username, password)
            elif (command == 'sendprivate'):
                sessionid = j[1].strip()
                usernameto = j[2].strip()
                message = ""
                for w in j[3:]:
                    message = "{} {}" . format(message, w)
                usernamefrom = self.sessions[sessionid]['username']
                logging.warning("SEND: session {} send message from {} to {}" . format(
                    sessionid, usernamefrom, usernameto))
                return self.send_message(sessionid, usernamefrom, usernameto, message)
            elif (command == 'sendgroup'):
                sessionid = j[1].strip()
                groupto = j[2].strip()
                message = ""
                for w in j[3:]:
                    message = "{} {}" . format(message, w)
                usernamefrom = self.sessions[sessionid]['username']
                logging.warning("SEND GROUP: session {} send message from {} to {}" . format(
                    sessionid, usernamefrom, groupto))
                return self.send_message_group(sessionid, usernamefrom, groupto, message)
            elif (command == 'sendfile'):
                sessionid = j[1].strip()
                usernameto = j[2].strip()
                encoded_content = j[3].strip()
                filepath = j[4].strip()
                usernamefrom = self.sessions[sessionid]['username']
                logging.warning("SEND FILE: session {} send file from {} to {}" . format(sessionid, usernamefrom, usernameto))
                return self.send_file(usernamefrom, usernameto, encoded_content, filepath)
            elif (command == 'receivefile'):
                sessionid = j[1].strip()
                username = self.sessions[sessionid]['username']
                logging.warning("RECEIVE FILE: Username {} received file" . format(username))
                return self.receive_file(username)
            elif(command == 'creategroup'):
                groupname = j[1].strip()
                logging.warning(
                    "CREATE GROUP: createing '{}' group" . format(groupname))
                return self.register_group(groupname)
            elif(command == 'joingroup'):
                sessionid = j[1].strip()
                groupname = j[2].strip()
                realmid = j[3].strip()
                username = self.sessions[sessionid]['username']
                # logging.warning("JOIN GROUP: {} {} {} {}" . format(sessionid, groupname, username, realmid))
                return self.join_group(username, groupname, realmid)
            elif (command == 'inbox'):
                sessionid = j[1].strip()
                username = self.sessions[sessionid]['username']
                logging.warning("INBOX: {}" . format(sessionid))
                return self.get_inbox(username)
            elif (command == 'inboxgroup'):
                sessionid = j[1].strip()
                groupname = j[2].strip()
                username = self.sessions[sessionid]['username']
                logging.warning("INBOX GROUP: {} {}" . format(username, groupname))
                return self.get_inbox_group(username, groupname)
            else:
                return {'status': 'ERROR', 'message': '**Protocol Tidak Benar'}
        except KeyError:
            return {'status': 'ERROR', 'message': 'Informasi tidak ditemukan'}
        except IndexError:
            return {'status': 'ERROR', 'message': '--Protocol Tidak Benar'}

    def autentikasi_user(self, username, password):
        user = self.user_db.get_by_key_value('username', username)
        print(user)
        if not user:
            return {'status': 'ERROR', 'message': 'user tidak ditemukan'}
        if user['password'] != password:
            return {'status': 'ERROR', 'message': 'password salah'}
        tokenid = str(uuid.uuid4())
        self.sessions[tokenid] = {'username': user['username']}
        return {'status': 'OK', 'token_id': tokenid, 'realm_id': user['realm_id']}
    
    def register_user(self, username, password):
        is_user_exist = self.get_user(username)
        if is_user_exist:
            return {'status': 'ERROR', 'message': 'user telah terdaftar'}
        else:
            new_user = {
                'username': username,
                'password': password,
                'realm_id': self.server_id
            }
            self.user_db.insert_data(new_user)
            print(new_user)
            return {'status': 'OK', 'realm_id': new_user['realm_id']}
    
    def join_group(self, username, groupname, realmid):
        # print(username, groupname, realmid)
        user = self.get_user(username)
        group = self.get_group(groupname)
        if(not user):
            return {'status': 'ERROR', 'message': 'User tidak ditemukan'}
        if(not group):
            return {'status': 'ERROR', 'message': 'Group tidak ditemukan'}
        group_user = {
            'username': user['username'],
            'groupname': group['name'],
            'realm_id': realmid
        }
        self.group_user_db.insert_data(group_user)
        return {'status': 'OK', 'message': 'User berhasil join group'}
    
    
    def register_group(self, groupname):
        is_group_exist = self.get_group(groupname)
        if is_group_exist:
            return {'status': 'ERROR', 'message': 'group telah terdaftar'}
        else:
            new_group = {
                'name': groupname,
            }
            self.group_db.insert_data(new_group)
            print(new_group)
            return {'status': 'OK', 'groupname':groupname}

    def get_user(self, username):
        user = self.user_db.get_by_key_value('username', username)
        if (not user):
            return False
        return user

    def get_group(self, groupname):
        group = self.group_db.get_by_key_value('name', groupname)
        if (not group):
            return False
        return group

    def send_message(self, sessionid, username_from, username_dest, message):
        if (sessionid not in self.sessions):
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        s_fr = self.get_user(username_from)
        s_to = self.get_user(username_dest)

        if (s_fr == False or s_to == False):
            return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}

        message = PrivateMessage(
            s_fr['username'],
            s_fr['realm_id'],
            s_to['username'],
            s_to['realm_id'],
            message
        )

        self.private_message_db.insert_data(message.toDict())

        return {'status': 'OK', 'message': 'Message Sent'}
    
    def send_file(self, username_from, username_to, encoded_content, filepath):
    
        s_fr = self.get_user(username_from)
        s_to = self.get_user(username_to)
    
        if (s_fr == False or s_to == False):
            return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}
    
        filename = os.path.basename(filepath)    

        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        folder_path = join(dirname(realpath(__file__)), "database/file_send/")
        os.makedirs(folder_path, exist_ok=True)
        new_file_name = f"{now}_{username_from}_{username_to}_{filename}"
        file_destination = join(folder_path, new_file_name)
        if "b" in encoded_content[0]:
            msg = encoded_content[2:-1]

            with open(file_destination, "wb") as fh:
                fh.write(base64.b64decode(msg))
        else:
            tail = encoded_content.split()

        message = FileMessage(
            s_fr['username'],
            s_fr['realm_id'],
            s_to['username'],
            s_to['realm_id'],
            new_file_name,
            file_destination
        )
    
        self.file_message_db.insert_data(message.toDict())

        return {'status': 'OK', 'message': 'File Sent'}
    
    def receive_file(self, username):
        folder_path = join(dirname(realpath(__file__)), "realm1/file_receive/", username)
        os.makedirs(folder_path, exist_ok=True)

        msgs = self.file_message_db.getall_by_key_value('receiver', username)
        # STUCK Masbro disini

        print(msgs)

        return {'status': 'OK', 'messages': msgs, 'received_files': folder_path}
    

    def send_message_group(self, sessionid, username_from, groupname_dest, message):
        if (sessionid not in self.sessions):
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        
        print(username_from, groupname_dest)
        
        isUserInGroup = self.group_user_db.is_user_exists_group(username_from, groupname_dest)
        if (isUserInGroup == False):
            return {'status': 'ERROR', 'message': 'User tidak memiliki akses ke grup ini'}
        
        s_fr = self.get_user(username_from)
        s_to = self.get_group(groupname_dest)

        if (s_fr == False or s_to == False):
            return {'status': 'ERROR', 'message': 'Grup Tidak Ditemukan'}

        message = GroupMessage(
            s_fr['username'],
            s_fr['realm_id'],
            s_to['name'],
            message
        )

        self.group_message_db.insert_data(message.toDict())

        return {'status': 'OK', 'message': 'Message Sent'}

    def get_inbox(self, username):
        msgs = self.private_message_db.get_by_key_value('receiver', username)
        return {'status': 'OK', 'messages': msgs}

    def get_inbox_group(self, username ,groupname):
        isUserInGroup = self.group_user_db.is_user_exists_group(username, groupname)
        if (isUserInGroup == False):
            return {'status': 'ERROR', 'message': 'User tidak memiliki akses ke grup ini'}

        msgs = self.group_message_db.getall_by_key_value('receiver_group', groupname)
        messages_list = self.list_messages(msgs)
        return {'status': 'OK', 'messages': messages_list}
    
    @staticmethod
    def list_messages(msgs):
        messages = ''
        for msg in msgs:
            messages +=  '['+ msg['sender'] + ': ' + msg['message'] + '], '
        return messages




if __name__ == "__main__":
    j = Chat()
    sesi = j.proses("auth messi surabaya")
    print(sesi)
    # sesi = j.autentikasi_user('messi','surabaya')
    # print sesi
    tokenid = sesi['tokenid']
    print(j.proses("send {} henderson hello gimana kabarnya son " . format(tokenid)))
    print(j.proses("send {} messi hello gimana kabarnya mess " . format(tokenid)))

    # print j.send_message(tokenid,'messi','henderson','hello son')
    # print j.send_message(tokenid,'henderson','messi','hello si')
    # print j.send_message(tokenid,'lineker','messi','hello si dari lineker')

    print("isi mailbox dari messi")
    print(j.get_inbox('messi'))
    print("isi mailbox dari henderson")
    print(j.get_inbox('henderson'))
