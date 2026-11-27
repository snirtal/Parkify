.PHONY: start stop shutdown reset

start:
	@bash scripts/live.sh start

stop:
	@bash scripts/live.sh stop

shutdown:
	@bash scripts/live.sh shutdown

reset:
	@bash scripts/live.sh reset
