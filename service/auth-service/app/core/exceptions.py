class EmailVerificationRequired(Exception):
    def __init__(
        self,
        token: str,
        user_email: str,
        user_name: str,
    ):
        self.token = token
        self.user_email = user_email
        self.user_name = user_name

        super().__init__(
            "Please verify your email before logging in"
        )