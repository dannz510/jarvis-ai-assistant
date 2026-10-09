import uvicorn
from core.config import get_config

def main():
    cfg = get_config()
    print("ASTRA Web starting at http://{}:{}".format(cfg.web_host, cfg.web_port))
    uvicorn.run("web.app:web_app", host=cfg.web_host, port=cfg.web_port, reload=False)

if __name__ == "__main__":
    main()
