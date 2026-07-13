### image-backend:1.0, image-frontend:1.0 이미지를 생성해서 Docker hub에 업로드 해보세요.

```bash
# 이미지 생성하기
docker build -t 계정/이미지명:tag .
# docker hub 에 push하기
docker push 계정/이미지명:tag

docker build -t yimjongwon/image-backend:1.0 .
docker build -t yimjongwon/image-frontend:1.0 .
docker push yimjongwon/image-backend:1.0
docker push yimjongwon/image-frontend:1.0


```