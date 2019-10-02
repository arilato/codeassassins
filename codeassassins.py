import requests
import re
import numpy as np
import json
import utils
import pickle
import slack
from datetime import date

char_min = 5
dictionary = utils.load_dictionary(char_min=char_min)
save_file = "SAVEFILE.pkl"

class User:
	def __init__(self, name: str, id_: str):
		self.name = name
		self.id = id_
		self.code = utils.load_random_word(dictionary)
		self.killed = []
		self.alive = True
		self.has_killed = False

	def set_target(self, target):
		self.target = target

	def get_status_string(self):
		if self.alive == False:
			return utils.set_status_message(self.alive, self.death_date, self.killer, self.killed)
		else:
			return utils.set_status_message(self.alive, None, None, self.killed)

class Game:
	def __init__(self, channel: str, weapon: str, shield: str):
		self.players_alive = []
		self.players_dead = []
		self.round = 1
		self.round_end = "October 11th, 11:59pm"
		self.round_start = date.today().strftime("%B %d, %Y")
		self.weapon = weapon
		self.shield = shield
		self.channel = channel
		self.channel_id = utils.get_channel_id(self.channel)
		self.admin_id = "U94MD12MV"
		self.end_string = "My job is done. They will now engage in a sockfight to" + \
				" the death at the next social."

		# initialize players
		member_ids, member_names = utils.get_channel_members(channel)
		for id_, name in zip(member_ids, member_names):
			self.players_alive.append(User(name, id_))

		# set targets by creating random permutation
		perm = np.random.permutation(len(self.players_alive))
		for i in range(len(self.players_alive)):
			self.players_alive[perm[i]].set_target(self.players_alive[perm[(i+1) % len(self.players_alive)]])

		# Message each player who their target is
		for player in self.players_alive:
			message = utils.set_target_message(player.target.name) + "\n"
			message += utils.set_codeword_message(player.code)
			utils.send_users_message([player.id], message)

		# Message channel
		utils.send_channel_message(self.channel_id, utils.create_welcome_message())

		# save game state
		save_game(self)

	def check(self):
		if len(self.players_alive) == 2:
			utils.send_channel_message(game.channel_id, "There are only two players left - %s and %s!" % 
				(self.players_alive[0].name, self.players_alive[1].name))
			utils.send_channel_message(game.channel_id, self.end_string)


	# user is id, not name
	def kill(self, user: str, code: str):
		for player in self.players_alive:
			if player.id == user:
				if player.target.code == code: # successful kill
					# announce to channel
					utils.send_channel_message(self.channel_id, \
						utils.set_channel_kill_message(player.name, player.target.name))
					# send success message
					message = utils.set_success_kill_message(player.target.name)
					utils.send_users_message([user], message)
					player.has_killed = True
					player.killed.append(player.target.name)
					# send death message, update killed person
					player.target.alive = False
					player.target.death_date = date.today().strftime("%B %d, %Y")
					player.target.killer = player.name
					message = "You have been killed."
					utils.send_users_message([player.target.id], message)
					self.players_alive.remove(player.target)
					self.players_dead.append(player.target)
					# update targets
					player.target = player.target.target
					message = utils.set_new_target_message(player.target.name)
					utils.send_users_message([user], message)
					save_game(self)
					self.check()
					return 1
				else:
					message = utils.set_fail_kill_message(player.target.name)
					utils.send_users_message([user], message)
					return 0
		return -1

	def end_round(self, new_round_date: str):
		self.round += 1
		self.round_start = date.today().strftime("%B %d, %Y")
		self.round_end = new_round_date

		players_to_remove = []

		for player in self.players_alive:
			print(player.name, player.has_killed)
			if player.has_killed == False:  # hasn't killed, kill the player
				utils.send_users_message([player.id], utils.set_thanos_message())
				utils.send_channel_message(self.channel_id, \
					utils.set_channel_kill_message("Thanos", player.target.name))	
				players_to_remove.append(player)			
				self.players_dead.append(player)				
			player.has_killed = False

		for player in players_to_remove:
			player.death_date = date.today().strftime("%B %d, %Y")
			player.killer = "Thanos"
			player.alive = False
			self.players_alive.remove(player)

		save_game(self)
		self.check()


def save_game(game: Game):
	with open(save_file, 'wb') as f:
		pickle.dump(game, f)


def load_game():
	with open(save_file, 'rb') as f:
		return pickle.load(f)


@slack.RTMClient.run_on(event='message')
def process_message(**payload):
	data = payload['data']
	web_client = payload['web_client']
	rtm_client = payload['rtm_client']

	user = data.get('user')
	message = data.get('text')

	if user is None:
		return

	# check prefixes
	message_words = message.split()
	if len(message_words) == 0:
		return

	elif message_words[0] == "!kill" and len(message_words) > 1:
		code = message_words[1]
		game.kill(user, code)

	elif message_words[0] == "!weapon":
		utils.send_users_message([user], utils.set_weapon_message(game.weapon))

	elif message_words[0] == "!shield":
		utils.send_users_message([user], utils.set_shield_message(game.shield))

	elif message_words[0] == "!round":
		utils.send_users_message([user], utils.set_round_message(game.round, game.round_start, game.round_end))

	elif message_words[0] == "!status":
		for player in game.players_alive + game.players_dead:
			if player.id == user:
				utils.send_users_message([user], player.get_status_string())
				return
		utils.send_users_message([user], "You were never playing! Your status is lame.")

	elif message_words[0] == "!target":
		for player in game.players_alive:
			if player.id == user:
				utils.send_users_message([user], utils.set_target_message(player.target.name))
				return
		utils.send_users_message([user], "You have no target - you're dead.")

	elif message_words[0] == "!alive":
		message = "Currently alive: \n"
		for player in  game.players_alive:
			message += "%s\n" % player.name
		utils.send_users_message([user], message)

	elif message_words[0] == "!help":
		utils.send_users_message([user], utils.create_help_message())

	elif user == game.admin_id and len(message_words) > 0:
		print("Admin speaking")
		if message_words[0] == "!round_end" and len(message_words) >= 2:
			game.end_round(message[len(message_words[0]) + 1:])
		elif message_words[0] == "!new_round_date" and len(message_words) >= 2:
			game.round_end = message[len(message_words[0]) + 1:]
			utils.send_channel_message(game.channel_id, "The round end date has been updated to %s!" \
				% game.round_end)
		elif message_words[0] == "!will_die":
			ndie = 0
			for player in game.players_alive:
				if player.has_killed == False:
					ndie += 1
			utils.send_users_message([game.admin_id], "%d die, %d total" %  (ndie, len(game.players_alive)))
		elif message_words[0] == "!set_weapon":
			game.weapon = message[len(message_words[0]) + 1:]
			utils.send_channel_message(game.channel_id, "The weapon has been updated to %s!" \
				% game.weapon)
		elif message_words[0] == "!set_shield":
			game.shield = message[len(message_words[0]) + 1:]
			utils.send_channel_message(game.channel_id, "The shield has been updated to %s!" \
				% game.shield)
		elif message_words[0] == "!set_end_words":
			game.end_string = message[len(message_words[0]) + 1:]
		save_game(game)

	else:
		utils.send_users_message([user], "Unrecognized command! Or maybe unformatted. I'm disappointed." + \
										 "Message !help for a list of available commands!")


if __name__ == "__main__":
	global game
	game = Game(channel = "test-slackbots", weapon = "fork", shield = "spoon")
	#game = load_game()

	rtm_client =  slack.RTMClient(token=utils.get_oauth_token())
	rtm_client.start()






