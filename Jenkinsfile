pipeline
{
	agent
	{
		label "master"
	}

	stages
	{
		stage("Test")
		{
			steps
			{
				script
				{
					version = sh (script: 'date +%-y.%-m.%-d.$(( $(date -d "1970-01-01 UTC $(date +%T)" +%s) / 2 ))', returnStdout: true, encoding: 'UTF-8').trim()

					shortHash = sh (script: "git rev-parse --short ${GIT_COMMIT}", returnStdout: true, encoding: "UTF-8").trim()

					echo "GIT_COMMIT='${GIT_COMMIT}'"
					echo "version='${version}'"
					echo "hash='${shortHash}'"

					version = dakcs.getVersion()
					shortHash = dakcs.getShortGitHash()

					echo "version='${version}'"
					echo "hash='${shortHash}'"
				}
			}
		}
	}
}
