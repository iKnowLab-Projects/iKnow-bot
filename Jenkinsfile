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
                        sh 'docker-compose up -d --build'
                    }
                }
            }
        }
    }
    
    post {
        success {
            echo 'Deployment successful!'
        }
        failure {
            echo 'Deployment failed.'
        }
    }
}
