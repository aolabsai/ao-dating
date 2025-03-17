FROM node:23

ARG VITE_BACKEND_URL

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of your source code
COPY . ./

# Set executable permission on the Vite binary AFTER copying the source
RUN chmod +x ./node_modules/.bin/vite

# Build the app
RUN npm run build

# Install serve globally to serve the built app
RUN npm install -g serve

EXPOSE 5173

# Default command to serve the build output
CMD ["serve", "-s", "dist", "-l",  "5173"]
