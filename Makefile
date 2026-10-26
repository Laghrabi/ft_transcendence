COMPOSE  = docker compose
ENV_FILE = .env

GREEN  = \033[0;32m
RED    = \033[0;31m
YELLOW = \033[0;33m
CYAN   = \033[0;36m
RESET  = \033[0m


up: env-check
	@echo "$(GREEN)Starting CareFlow...$(RESET)"
	$(COMPOSE) up --build -d
	@echo "$(GREEN)CareFlow is running!$(RESET)"

down:
	@echo "$(YELLOW)Stopping containers...$(RESET)"
	$(COMPOSE) down
	@echo "$(YELLOW)Containers stopped.$(RESET)"

build:
	@echo "$(CYAN)Rebuilding all images...$(RESET)"
	$(COMPOSE) build --no-cache

logs:
	$(COMPOSE) logs -f

restart:
	$(COMPOSE) restart

status:
	$(COMPOSE) ps

clean: down
	@echo "$(RED)Removing volumes...$(RESET)"
	$(COMPOSE) down -v --remove-orphans
	@echo "$(RED)Clean complete.$(RESET)"

fclean: clean
	@echo "$(RED)Removing all Docker artifacts...$(RESET)"
	docker system prune -af --volumes
	@echo "$(RED)Full clean complete.$(RESET)"

re: fclean up

.PHONY: up down build logs restart status clean fclean re env-check