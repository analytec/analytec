heroku git:remote -a analytec
git add .
git commit -m "update"
git push origin master
git push heroku master
heroku restart
heroku ps:scale web=1
heroku ps:scale worker=1
heroku logs --tail
