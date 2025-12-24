pipeline {
    agent any
    
    stages {
        stage('Checkout') {
            steps {
                git branch: 'develop', url: 'https://github.com/iKnowLab-Projects/iKnow-bot.git'
            }
        }
        
        stage('Deploy') {
            steps {
                script {
                    dir('llm-stack') {
                        // Inject secrets from Host (mounted in Jenkins container)
                        sh 'cp /var/jenkins_home/.env.production .env'
                        sh 'docker-compose up -d --build'
                    }
                }
            }
        }
    }
    
    post {
        success {
            echo 'Deployment successful!'
            script {
                // Load .env to get Webhook URL (if exists)
                def webhookUrl = sh(script: "grep DISCORD_WEBHOOK_URL llm-stack/.env | cut -d '=' -f2", returnStdout: true).trim()
                
                if (webhookUrl) {
                    def payload = '{"content": "✅ **Deployment Successful!**\\nNew version of iKnow-bot is now live."}'
                    sh "curl -H 'Content-Type: application/json' -d '${payload}' ${webhookUrl}"
                } else {
                    echo 'No DISCORD_WEBHOOK_URL found in .env, skipping notification.'
                }
            }
        }
        failure {
            echo 'Deployment failed.'
        }
    }
}
