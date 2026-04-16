FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# expose Vite default port 5173
CMD ["npm", "run", "dev", "--", "--host"]