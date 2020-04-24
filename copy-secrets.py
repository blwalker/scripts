import argparse
import base64
import boto3
import docker
import shlex
import subprocess

class Secret(object):
	name = ''
	description = ''
	value = ''

	def __init__(self, name, description):
		self.name = name
		self.description = description

	def getSecret(self, awsClient):
		print(f'Getting secret value for {self.name}')
		response = awsClient.get_secret_value(SecretId = self.name)

		self.value = response['SecretString']

	def createOrionSecret(self, awsClient, profile):
		newName = self.name.replace('aurora', 'orion')
		print(f'Saving secret {newName}')

		awsClient.create_secret(Name = newName,
			Description = self.description,
			SecretString = self.value.replace('AURORA', 'ORION').replace('aurora', 'orion'))

def getSecrets(awsClient):
	print('Getting all secrets')
	paginator = awsClient.get_paginator('list_secrets')
	iterator = paginator.paginate(MaxResults = 100)

	secrets = []

	for page in iterator:
		for secret in page['SecretList']:
			if 'aurora' in secret['Name']:
				secrets.append(Secret(secret['Name'], secret['Description']))

	[secret.getSecret(awsClient) for secret in secrets]

	secrets.sort(key = lambda x: x.name)
	return secrets

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('-p', '--profile', required = True)
	args = parser.parse_args()

	session = boto3.Session(profile_name = args.profile)
	awsClient = session.client('secretsmanager')

	secrets = getSecrets(awsClient)

	[secret.createOrionSecret(awsClient, args.profile) for secret in secrets]

if __name__ == '__main__':
	main()
