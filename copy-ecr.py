import argparse
import base64
import boto3
import docker
import shlex
import subprocess

class Repository(object):
	oldName = ""
	newName = ""
	uri = ""
	tags = []

	def __init__(self, uri):
		location = uri.index('/')

		self.oldName = uri[location+1:]
		self.newName = self.oldName.replace('aurora', 'orion')
		self.uri = uri[0:location]

	def getImages(self, awsClient):
		print(f'Getting all tags for {self.oldName}')
		paginator = awsClient.get_paginator('list_images')
		iterator = paginator.paginate(maxResults = 100, repositoryName = self.oldName)

		self.tags = []

		for page in iterator:
			for image in page['imageIds']:
				if 'imageTag' in image:
					self.tags.append(image['imageTag'])

	def pullImages(self, dockerClient):
		for tag in self.tags:
			name = f'{self.uri}/{self.oldName}'
			print(f'Pulling {name}:{tag}')
			dockerClient.images.pull(f'{name}', tag = tag)

	def pushImages(self, dockerClient, dockerApiClient):
		for tag in self.tags:
			newName = f'{self.uri}/{self.newName}'
			oldTag = f'{self.uri}/{self.oldName}:{tag}'
			newTag = f'{newName}:{tag}'
			
			print(f'Creating tag {newTag}')
			dockerApiClient.tag(oldTag, newTag)

			print(f'Pushing {newName}:{tag}')
			dockerClient.images.push(f'{newName}', tag = tag)

	def createRegistry(self, awsClient, profile):
		tags = []
		lifecyclePolicy = None

		if profile == 'dev':
			tags.append({
				'Key': 'BillingKey',
				'Value': 'Dev-Pipeline'
			})

			with open('lifecycle-policy-dev.json', 'r') as file:
				lifecyclePolicy = file.read()
		elif profile == 'prod' or profile == 'orion':
			tags.append({
				'Key': 'BillingKey',
				'Value': 'Orion'
			})

		try:
			print(f'Creating ECR registry {self.newName}')
			response = awsClient.create_repository(repositoryName = self.newName,
				imageTagMutability = 'MUTABLE',
				imageScanningConfiguration = {
					'scanOnPush': True
				})
		except awsClient.exceptions.RepositoryAlreadyExistsException:
			print(f'{self.newName} already exists, skipping')
			return

		if 'repository' not in response or 'repositoryArn' not in response['repository']:
			raise Exception(f'Failed to get repositoryArn of newly created registry {self.newName}')

		if len(tags) > 0:
			print(f'Adding tags to {self.newName}')
			awsClient.tag_resource(resourceArn = response['repository']['repositoryArn'], tags = tags)

		if lifecyclePolicy:
			print(f'Adding lifecycle policy to {self.newName}')
			awsClient.put_lifecycle_policy(repositoryName = self.newName, lifecyclePolicyText = lifecyclePolicy)

def getRepositories(awsClient):
	print('Getting all repositories')
	paginator = awsClient.get_paginator('describe_repositories')
	iterator = paginator.paginate(maxResults = 100)

	allRepositories = []

	for page in iterator:
		for repo in page['repositories']:
			if 'aurora' in repo['repositoryName']:
				allRepositories.append(Repository(repo['repositoryUri']))

	allRepositories.sort(key = lambda x: x.oldName)
	return allRepositories

def logoutOfDocker(uri):
	print('Logging out of docker')

	subprocess.run(shlex.split(f'docker logout {uri}'))

def loginToDocker(awsClient):
	print('Logging in to docker')
	token = awsClient.get_authorization_token()
	
	if not token or 'authorizationData' not in token:
		raise Exception('Failed to get ecr auth token.')

	auth = token['authorizationData'][0]
	username, password = base64.b64decode(auth['authorizationToken']).decode().split(':')
	registry = auth['proxyEndpoint']

	dockerClient = docker.from_env()
	dockerClient.login(username, password, registry = registry)

	return dockerClient

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('-p', '--profile', required = True)
	args = parser.parse_args()

	session = boto3.Session(profile_name = args.profile)
	awsClient = session.client('ecr')

	repositories = getRepositories(awsClient)
	[repo.getImages(awsClient) for repo in repositories]

	[repo.createRegistry(awsClient, args.profile) for repo in repositories]

	logoutOfDocker(repositories[0].uri)
	dockerClient = loginToDocker(awsClient)

	[repo.pullImages(dockerClient) for repo in repositories]

	dockerApiClient = docker.APIClient()
	[repo.pushImages(dockerClient, dockerApiClient) for repo in repositories]

if __name__ == '__main__':
	main()
