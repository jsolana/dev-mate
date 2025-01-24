# dev-mate

`DevMate` is your friendly assistant for managing repositories. From tagging issues to adding comments, `DevMate` streamlines collaboration and helps developers stay organized. Whether you're handling pull requests, tracking bugs, or reviewing code, `DevMate` is here to make your workflow smoother and more efficient.

## Build

Run `pip install -r requirements.txt`.

### Receiving Real Traffic from GitLab

To receive real traffic from GitLab, you can use **Ngrok**, which allows you to expose your local server to the internet. Follow these steps:

1. Install Ngrok by downloading it from the official website and extracting the binary.

2. Start Ngrok by running the following command:

```batch
ngrok http <port-number>
```

Replace  `port-number` with the port your Go application is running on. By default, `8080`.

**Ngrok** will generate a public URL (e.g., `http://random-string.ngrok-free.app`).
