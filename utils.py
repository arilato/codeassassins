import requests
import re
import numpy as np
import json

oauth_file_name = "API.token"
admin_file_name = "ADMIN.token"
dictionary_file_name = "dictionary.txt"
api_pre = "https://slack.com/api/"


###########################################################################
#									AUTH			 					  #
###########################################################################

# gets global API token by file
def get_oauth_token(file_name: str = oauth_file_name):
	with open(file_name, "r") as f:
		return re.sub(r'[^a-zA-Z0-9-]+', '', f.readline())

# gets secret admin pw by file
def get_admin_token(file_name: str = admin_file_name):
	with open(file_name, "r") as f:
		return re.sub(r'[^a-zA-Z0-9-]+', '', f.readline())

TOKEN = get_oauth_token()
#ADMIN = get_admin_token()

###########################################################################
#								DICTIONARY			 					  #
###########################################################################

# loads all words from dictionary given minimum character limit
def load_dictionary(file_name: str = dictionary_file_name, char_min: int = 5):
	words = []
	with open(file_name, "r") as f:
		for line in f:
			word = re.sub(r'[^a-zA-Z0-9-]+', '', line)
			if len(word) >= char_min:
				words.append(word)
	return words

def load_random_word(dictionary: [str]):
	return dictionary[np.random.randint(len(dictionary))]

###########################################################################
#								CH/USR ID			 					  #
###########################################################################

# given channel name, gets internal slack id value 
def get_channel_id(name: str):
	URL = api_pre + "conversations.list"
	PARAMS = {
		'token': TOKEN,
		'limit': 1000,
	}
	r = requests.get(url = URL, params = PARAMS)
	data = r.json()
	for ch in data['channels']:
		if ch['name'] == 'test-slackbots':
			return ch['id']
	return -1

# given a user id, gets the actual name of user
def get_user_name(user_id: str):
	URL = api_pre + "users.info"
	PARAMS = {
		'token': TOKEN,
		'user': user_id,
	}
	r = requests.get(url = URL, params = PARAMS)
	data = r.json()
	if data['user']['is_bot']:
		return -1
	return data['user']['real_name']

# gets ids and names of all members in a channel
def get_channel_members(name: str):
	ch_id = get_channel_id(name)
	URL = api_pre + "channels.info"
	PARAMS = {
		'token': TOKEN,
		'channel': ch_id,
	}
	r = requests.get(url = URL, params = PARAMS)
	data = r.json()
	member_ids = data['channel']['members']

	member_names = [get_user_name(user_id) for user_id in member_ids]
	member_ids = [user_id for user_id, member_name in zip(member_ids, member_names) if member_name != -1]
	member_names = [member_name for member_name in member_names if member_name != -1]

	return member_ids, member_names


###########################################################################
#								MESSAGING			 					  #
###########################################################################

# sets up a message to notify what the current weapon is
def set_weapon_message(weapon: str):
	return "The current weapon is %s!" % weapon

# sets up a message to notify what the current weapon is
def set_shield_message(shield: str):
	return "The current shield is %s!" % shield

# sets up a message to notify players of their target
def set_target_message(target_name: str):
	return "Your current target is %s!" % target_name

#sets up a message to notify players of their target
def set_new_target_message(target_name: str):
	return "Your new target is %s!" % target_name

# sets up message to give information on current round
def set_round_message(round_n: int, round_start: str, round_end: str):
	return "This is currently round %d, which started on %s. \
		It will be ending on %s." % (round_n, round_start, round_end)

# sets up thanos message
def set_thanos_message():
	return "You have been snapped by Thanos for not contributing to his cause!\n \
		(You did not kill anyone this round so you died). "

def set_channel_kill_message(player1: str, player2: str):
	if player1 == "Thanos":
		return "%s has snapped %s!" % (player1, player2)
	return "%s has assassinated %s!" % (player1, player2)

#sets up message for sending status
def set_status_message(alive: bool, death_date: str, killer: str, killed: [str]):
	if len(killed) == 0:
		kill_string = "You have killed no one!  "
	else:
		kill_string = "You have %d kills - " % len(killed)
	for player in killed:
		kill_string += player + ", "
	kill_string = kill_string[:-2]

	if alive:
		return "You are currently alive! " + kill_string
	else:
		returns = "You are dead! You were killed by %s on %s. " % (killer, death_date)
		return returns + kill_string

# sets up message for when you kill a user successfully
def set_success_kill_message(user: str):
	return "You have successfully killed %s!" % user

# sets up message for when you fail to kill a user
def set_fail_kill_message(user: str):
	return "You have failed to kill %s! Wrong codeword :(" % user

# sets up a message to notify players of their code
def set_codeword_message(code: str):
	message_text = "Your secret codeword is *%s*. Do not give this away to " % code
	message_text += "anyone except the person that assassinates you. Whoever has "
	message_text += "this codeword can take you out of the game!"
	return message_text

def create_welcome_message():
	message_text = "@channel\nHello assassins! The game has just begun, and everyone should have a target. " + \
				   "A quick refresher on the rules (full details can be found on the rulebook pinned " + \
				   "in this channel): \n1. You must kill once per round, or you will be snapped away.\n" + \
				   "2. You must touch your target with the assassination weapon to assassinate them. " + \
				   "If they are holding the shield item, they are protected from you. You *cannot* tape " + \
				   "a shield item to yourself, or stick it to you, etc. You *must hold it*.\n 3. " + \
				   "Everyone has a codeword that they must protect. If you get assassinated, you must " + \
				   "give your codeword to your assassin, so they can verify they assassinated you.\n" + \
				   "4. Post a selfie with your target when you assassinate them to this channel!\n5. " + \
				   "When there are two players left, we will have a special event prepared.\n" + \
				   "That's all, and happy hunting!"
	return message_text

def create_help_message():
	message_text = "Your possible commands are:\n" + \
				   "1. *!weapon* - shows the current round's assassination weapon.\n" + \
				   "2. *!shield* - shows the current round's assassination shield.\n" + \
				   "3. *!round* - shows the current round's information.\n" + \
				   "4. *!status* - shows your current status.\n" + \
				   "5. *!target* - shows who your current target is.\n" + \
				   "6. *!kill <code>* - kills your target, given their code. \n"
	return message_text


# sends a message to a group of users. Must be user ids, not names
def send_users_message(users: [str], message: str):
	# open the channel
	URL = api_pre + "conversations.open"
	user_str = ",".join(users)
	DATA = {
		"token": TOKEN,
		"users": user_str,
	}
	data = requests.post(url = URL, data=DATA).json()
	if not data['ok']:
		return -1

	channel_id = data['channel']['id']
	URL = api_pre + "chat.postMessage"
	DATA = {
		"token": TOKEN,
		"channel": channel_id,
		"text": message,
	}
	return requests.post(url = URL, data=DATA).json()

# sends message to a channel, Takes in the channel (id, not name), and message as string
def send_channel_message(channel: str, message: str):
	URL = api_pre + "chat.postMessage"
	DATA = {
		"token": TOKEN,
		"channel": channel,
		"text": message,
	}
	return requests.post(url = URL, data=DATA).json()






