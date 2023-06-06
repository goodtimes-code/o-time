#!/bin/bash
echo Starting redis server... 
#docker run -d --rm --name=redis-server -p 6379:6379 redis
brew services restart redis
redis-cli ping