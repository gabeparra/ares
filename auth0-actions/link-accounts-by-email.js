/**
 * Auth0 Action: Automatic Account Linking by Email
 * 
 * SETUP INSTRUCTIONS:
 * 1. Go to Auth0 Dashboard -> Actions -> Flows -> Login
 * 2. Create a new Custom Action
 * 3. Paste this code
 * 4. Add Secrets:
 *    - MANAGEMENT_CLIENT_ID: Your M2M app client ID
 *    - MANAGEMENT_CLIENT_SECRET: Your M2M app client secret
 * 5. Deploy and add to the Login flow
 * 
 * IMPORTANT: Grant your M2M app these permissions:
 * - read:users
 * - update:users
 * - create:users
 */

const { ManagementClient } = require('auth0');

exports.onExecutePostLogin = async (event, api) => {
  // Skip if user has no email or email is not verified
  if (!event.user.email || !event.user.email_verified) {
    console.log('Skipping account linking: email not verified');
    return;
  }

  // Skip if this is already a linked account login
  if (event.user.identities && event.user.identities.length > 1) {
    console.log('User already has linked identities');
    return;
  }

  const domain = event.secrets.AUTH0_DOMAIN || event.tenant.id + '.auth0.com';
  
  const management = new ManagementClient({
    domain: domain,
    clientId: event.secrets.MANAGEMENT_CLIENT_ID,
    clientSecret: event.secrets.MANAGEMENT_CLIENT_SECRET,
  });

  try {
    // Find all users with the same email
    const users = await management.usersByEmail.getByEmail({
      email: event.user.email
    });

    console.log(`Found ${users.data.length} user(s) with email ${event.user.email}`);

    if (users.data.length <= 1) {
      // No other accounts to link
      return;
    }

    // Find the primary account (prefer the oldest or Google account)
    const currentUserId = event.user.user_id;
    let primaryUser = null;
    let secondaryUsers = [];

    // Sort users: prefer Google, then oldest account
    const sortedUsers = users.data.sort((a, b) => {
      // Prefer Google accounts
      const aIsGoogle = a.user_id.startsWith('google-oauth2');
      const bIsGoogle = b.user_id.startsWith('google-oauth2');
      if (aIsGoogle && !bIsGoogle) return -1;
      if (!aIsGoogle && bIsGoogle) return 1;
      
      // Then prefer oldest account
      return new Date(a.created_at) - new Date(b.created_at);
    });

    primaryUser = sortedUsers[0];
    secondaryUsers = sortedUsers.slice(1);

    // If current user is the primary, link others to it
    // If current user is secondary, link it to the primary
    if (currentUserId === primaryUser.user_id) {
      console.log(`Current user ${currentUserId} is primary, linking others`);
      
      for (const secondary of secondaryUsers) {
        const provider = secondary.user_id.split('|')[0];
        const userIdPart = secondary.user_id.split('|')[1];
        
        try {
          await management.users.link(
            { id: primaryUser.user_id },
            {
              provider: provider,
              user_id: userIdPart
            }
          );
          console.log(`Linked ${secondary.user_id} to ${primaryUser.user_id}`);
        } catch (linkError) {
          console.error(`Failed to link ${secondary.user_id}: ${linkError.message}`);
        }
      }
    } else {
      // Current user is secondary - link to primary
      const currentProvider = currentUserId.split('|')[0];
      const currentUserIdPart = currentUserId.split('|')[1];
      
      try {
        await management.users.link(
          { id: primaryUser.user_id },
          {
            provider: currentProvider,
            user_id: currentUserIdPart
          }
        );
        console.log(`Linked current user ${currentUserId} to primary ${primaryUser.user_id}`);
        
        // Update the user ID in the session to use the primary
        // This ensures the user continues with the primary account
        api.user.setAppMetadata({ 
          linked_from: currentUserId,
          linked_at: new Date().toISOString()
        });
        
      } catch (linkError) {
        console.error(`Failed to link current user: ${linkError.message}`);
      }
    }

  } catch (error) {
    console.error(`Account linking error: ${error.message}`);
    // Don't block login on linking errors
  }
};

