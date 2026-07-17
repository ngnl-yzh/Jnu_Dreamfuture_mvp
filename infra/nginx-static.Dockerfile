# 정적 웹 MVP 샌드박스 이미지 템플릿.
# 빌드 컨텍스트에 압축 해제된 정적 파일(site/)을 두고 빌드한다.
FROM nginx:1.27-alpine

# 비루트 실행을 위한 권한 정리
RUN chown -R nginx:nginx /var/cache/nginx /var/log/nginx /etc/nginx/conf.d \
    && touch /var/run/nginx.pid && chown nginx:nginx /var/run/nginx.pid

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY site/ /usr/share/nginx/html/

USER nginx
EXPOSE 8080
