@rem ===========================================================================
@rem Gradle wrapper bootstrap (Windows).
@rem
@rem See ./gradlew for the rationale on why the wrapper JAR is not shipped
@rem in the template stamp. Run `gradle wrapper --gradle-version 8.7` once
@rem after stamping to populate gradle\wrapper\gradle-wrapper.jar.
@rem ===========================================================================
@if "%DEBUG%"=="" @echo off
setlocal

set DIRNAME=%~dp0
set APP_HOME=%DIRNAME%
set WRAPPER_JAR=%APP_HOME%gradle\wrapper\gradle-wrapper.jar

if not exist "%WRAPPER_JAR%" (
  echo [FAIL] %WRAPPER_JAR% is missing. 1>&2
  echo        Run `gradle wrapper --gradle-version 8.7` once to populate it. 1>&2
  exit /b 1
)

set JAVA_EXE=java.exe
if defined JAVA_HOME set JAVA_EXE=%JAVA_HOME%\bin\java.exe

"%JAVA_EXE%" -classpath "%WRAPPER_JAR%" -Dorg.gradle.appname=gradlew org.gradle.wrapper.GradleWrapperMain %*
endlocal
