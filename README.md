# Cloud Computing Assignment #2

By:
Tamir Ben Ari

### Task:
In this exercise, you’ll need to build a caching system to store users’ session data. The session data is addressable by key (the user id) and can range in size between
0.5 KB – 8 KB of data.

The API you’ll need to support is composed of the following functions:
- put (str_key, data, expiration_date)
- get(str_key) → null or data

You can expose these functions as rest endpoints, or use any RPC mechanism you desire.
The code behind these endpoints will run on multiple EC2 instances and you need to orchestrate the data between them.

To pass, your solution needs to be able to handle, without data loss, the following scenarios:
- Putting and getting data across multiple keys, that will reside in different nodes.
- Losing a node and not losing any data
- Adding a new node to the system and extending its capacity

The client of the caching service has a single endpoint that it is aware of, you cannot do client-side load balancing. You are free to do load balancing in your code or using the cloud infrastructure to do that.
You do not have to worry about persistence, the data can be kept purely in memory.
You do not have to worry about consistency or concurrency, a read may get an older version of the data, as long as eventually we’ll read the latest version.




*Cloud Formation:*
- [Template Anatomy](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-anatomy.html)
- [Ec2 template snippet](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-ec2-instance.html)
- [Cloud Formation designer](https://us-east-2.console.aws.amazon.com/cloudformation/designer/home?region=us-east-2)
