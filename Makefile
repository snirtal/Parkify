.PHONY: start stop shutdown

start:
	@bash scripts/live.sh start

stop:
	@bash scripts/live.sh stop

shutdown:
	@bash scripts/live.sh shutdown
