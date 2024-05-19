
def rtsp_builder(user_name, password, ip_address, port) -> str:
    return f'rtsp://{user_name}:{password}@{ip_address}:{port}/live/av1'