def getVersion()
{
    now = new Date()
    midnight = new Date()
    midnight.clearTime()

    duration = groovy.time.TimeCategory.minus(now, midnight)
    seconds = (int)(duration.toMilliseconds() / 2000)

	duration = null
    return now.format("yy.M.d.") + "${seconds}"
}

def getShortGitHash(String longHash)
{
    return sh (script: "git rev-parse --short ${longHash}", returnStdout: true, encoding: "UTF-8").trim()
}