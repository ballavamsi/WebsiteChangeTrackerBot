docker-compose -f .\docker-compose-local.yml down 
REM docker system prune -a -f
docker-compose -f .\docker-compose-local.yml build
docker-compose -f .\docker-compose-local.yml up -d