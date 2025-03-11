FROM node:23

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

# Default command to serve the build output
CMD ["serve", "-s", "dist"]
