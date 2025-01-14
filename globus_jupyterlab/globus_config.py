import os
import logging
import pickle
import base64
from typing import List

import globus_sdk
from globus_sdk.scopes import TransferScopes

log = logging.getLogger(__name__)


class GlobusConfig():
    """
    Track all Globus Related information related to the Globus Jupyterlab
    server extension. Many settings can be re-configured via environment
    variables where JupyterLab is being run. For example: 

    .. code-block::
    
        $ export GLOBUS_REFRESH_TOKENS=true
        $ jupyter lab
    """
    default_client_id = '64d2d5b3-b77e-4e04-86d9-e3f143f563f7'
    base_scopes = [
        TransferScopes.all
    ]

    def get_refresh_tokens(self) -> bool:
        """
        Should Jupyterlab use Refresh tokens? Default is False. When True,
        JupyterLab will automatically refresh access tokens, eliminating the
        need for additional user authentications to refresh tokens.

        Configurable via evironment variable: GLOBUS_REFRESH_TOKENS

        Acceptable values:

          * 'true' -- use refresh tokens
          * 'false' -- do not use refresh tokens
        """
        refresh_tokens = os.getenv('GLOBUS_REFRESH_TOKENS', False)
        return True if refresh_tokens == 'true' else False
    
    def get_named_grant(self) -> str:
        """
        Set a custom Named Grant when a user logs into Globus. Changes the pre-filled
        text displayed on the Globus Consent page when logging in.

        Configurable via evironment variable: GLOBUS_NAMED_GRANT
        """
        return os.getenv('GLOBUS_NAMED_GRANT', 'Globus JupyterLab')

    def get_scopes(self) -> List[str]:
        scopes = self.base_scopes.copy()
        custom_transfer_scope = self.get_transfer_submission_scope()
        if custom_transfer_scope:
            scopes.append(custom_transfer_scope)
        return scopes

    def get_transfer_submission_url(self) -> str:
        """
        By default, JupyterLab will start transfers on the user's
        behalf using the Globus Transfer API directly. Configure this to instead
        use a custom Globus Resource Server for submitting transfers on the user's
        behalf. 

        Note: GLOBUS_TRANSFER_SUBMISSION_SCOPE must also be configured. 

        Configurable via evironment variable: GLOBUS_TRANSFER_SUBMISSION_URL
        """
        return os.getenv('GLOBUS_TRANSFER_SUBMISSION_URL', None)

    def get_transfer_submission_scope(self) -> str:
        """
        Define a custom 'transfer submission' scope for submitting user
        transfers. Used in conjunction with GLOBUS_TRANSFER_SUBMISSION_URL.
        Includes a custom scope to use when logging in and submitting transfers.
        Transfers submitted to the custom URL will be authorized with the access
        token for this custom scope instead of a Globus Transfer access token.

        Configurable via evironment variable: GLOBUS_TRANSFER_SUBMISSION_SCOPE
        """
        custom_scope = os.getenv('GLOBUS_TRANSFER_SUBMISSION_SCOPE', None)
        if custom_scope and not self.get_transfer_submission_url():
            raise ValueError(
                'GLOBUS_TRANSFER_SUBMISSION_URL set without a custom scope! Set '
                'a custom scope with GLOBUS_TRANSFER_SUBMISSION_SCOPE'
            )
        return custom_scope

    def get_transfer_submission_is_hub_service(self) -> str:
        """
        Defines how Jupyterlab should authorize with the custom submission service. If
        the Globus Resource Server is embedded inside a hub service, set this to 'true'
        in order to use the 'hub' token for authorization with the hub (Hub token will
        be passed in the header under Authorization). The Globus token will be passed 
        instead in POST data.

        If false, submission will not use the hub token, and assume the remote service
        is a normal Globus resource server, and pass the token in the header under
        the name "Authorization".

        Configurable via evironment variable: GLOBUS_TRANSFER_SUBMISSION_IS_HUB_SERVICE

        .. code-block::

        Acceptable values:

        * ‘true’ – use refresh tokens
        * ‘false’ – do not use refresh tokens
        """
        val = os.getenv('GLOBUS_TRANSFER_SUBMISSION_IS_HUB_SERVICE', None)
        return True if val == 'true' else False

    def get_named_grant(self) -> str:
        return os.getenv('GLOBUS_NAMED_GRANT', 'Globus JupyterLab')

    def get_hub_token(self) -> str:
        """
        Fetch the Jupyter API 'hub' token when JuptyerHub starts a single-user-server.

        This value is provided by JupyterHub and probably should not be set manually.

        Searches for value named: JUPYTERHUB_API_TOKEN
        """
        return os.getenv('JUPYTERHUB_API_TOKEN', '')

    def get_client_id(self) -> str:
        """
        Defines the Client ID Globus Jupyterlab will use. This can be swapped
        out with a custom Globus Native App client ID if desired.

        Do not use a JupyterHub Client ID or other non-native app credentials,
        as JupyterLab is its own Globus App does its own Login and should not
        impersonate other apps.

        Configurable via evironment variable: GLOBUS_CLIENT_ID
        """
        return os.getenv('GLOBUS_CLIENT_ID', self.default_client_id)

    def get_redirect_uri(self) -> str:
        """
        This is the OAuth2 redirect URI which Globus Auth uses after
        successful login. By default, this is automatically determined
        depending on the environment. 

        In a "hub" environment, the user is redirected to the Globus 'auth code'
        redirect url for manually copy-pasting a code to finish login.

        In a non-"hub" environment, the redirect URL is automatically determined
        based on the Globus Jupyterlab callback handler. Usually:
        http://localhost:8888/lab/globus-jupyterlab/oauth_callback
        The 'auth code' is automatically copied for the user during login.

        Admins should note that the 'automatic' behavior cannot be used in most
        hub environments due to Globus Apps (And basically the OAuth2 Spec) requiring
        static callback URLs. Hub URLs are usually dynamic, including the username in
        the URLs (https://myhub.com/user/<username>/lab). Note this limitation when
        using custom redirect URIs. For this reason in most cases, this should not be 
        changed and left to JupyterLab to automatically determine instead.

        Configurable via evironment variable: GLOBUS_REDIRECT_URIS
        """
        return os.getenv('GLOBUS_REDIRECT_URI', None)

    def is_gcp(self) -> str:
        return bool(self.get_gcp_collection())

    def get_gcp_collection(self) -> str:
        return globus_sdk.LocalGlobusConnectPersonal().endpoint_id

    def get_collection_id_owner(self) -> str:
        owner_info = globus_sdk.LocalGlobusConnectPersonal().get_owner_info()
        if owner_info:
            return owner_info.id
        return None

    def get_local_globus_collection(self) -> str:
        return (
            self.get_gcp_collection() or
            self.get_oauthenticator_data().get('endpoint_id') or
            None
        )

    def get_collection_base_path(self) -> str:
        return os.getcwd()

    def is_hub(self) -> bool:
        """Returns True if JupyterLab is running in a 'hub' environment, false otherwise"""
        # There may be a better way to ensure this is a hub environment. It may be possible
        # that the server admin is running without users and hub tokens are disabled, and this
        # could possibly return a false negative, although that should be unlikely.
        return os.getenv('JUPYTERHUB_USER', None) and self.get_hub_token()

    def get_oauthenticator_data(self) -> dict:
            # Fetch any info set by the Globus Juptyterhub OAuthenticator
        oauthonticator_env = os.getenv('GLOBUS_DATA')
        if oauthonticator_env:
            try:
                return pickle.loads(base64.b64decode(oauthonticator_env))
            except pickle.UnpicklingError:
                log.error('Failed to load GLOBUS_DATA', exc_info=True)
        return dict()
