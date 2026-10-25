"""Adapt a synchronous SQL test session to the async repository interface."""


class SessionAdapter:
    """Use the production SQL queries with an in-memory synchronous driver."""

    def __init__(self, session):
        self.session = session

    async def execute(self, statement):
        return self.session.execute(statement)

    async def rollback(self):
        self.session.rollback()
